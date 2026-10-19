"""Staged orchestration for the offline corpus ingestion pipeline."""

import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from pipeline.artifact_validation import validate_corpus_artifacts
from pipeline.chunking.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MIN_TOKENS,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
    PROJECT_ROOT,
)
from pipeline.chunking.io_jsonl import read_jsonl


class StageName(StrEnum):
    """Named stages in the canonical offline corpus flow."""

    DOCX_INGESTION = "docx_ingestion"
    MARKDOWN_CLEANUP = "markdown_cleanup"
    PARENT_CHUNKING = "parent_chunking"
    REGEX_CHILD_CHUNKING = "regex_child_chunking"
    TABLE_REFERENCE_AUDIT = "table_reference_audit"
    TABLE_MARKDOWN_CONVERSION = "table_markdown_conversion"
    TABLE_DOCUMENT_BUILD = "table_document_build"
    CHROMA_INDEXING = "chroma_indexing"
    BM25_INDEXING = "bm25_indexing"
    CORPUS_VALIDATION = "corpus_validation"
    PREFLIGHT = "preflight"
    PUBLICATION = "publication"


LIFECYCLE_PHASES = (StageName.PREFLIGHT, StageName.PUBLICATION)
STAGE_ORDER = tuple(stage for stage in StageName if stage not in LIFECYCLE_PHASES)

# Entradas publicadas que el build regenera; el resto de data/ nunca se toca
MANAGED_ENTRIES = {
    "interim": ("tables",),
    "processed": (
        "chunks/parents.jsonl",
        "chunks/regex_constrained_semantic",
        "tables_markdown",
        "table_documents.jsonl",
        "chroma",
        "bm25",
    ),
}


@dataclass(frozen=True)
class StageEvent:
    """One lifecycle transition emitted by a named stage."""

    stage: str | StageName
    number: int | None
    status: str
    detail: str = ""


@dataclass(frozen=True)
class StageResult:
    """Completed stage result retained for progress reporting."""

    stage: StageName
    value: Any


@dataclass(frozen=True)
class BuildPaths:
    """Published and isolated staging paths for one corpus build."""

    project_root: Path
    run_id: str

    @property
    def workspace(self) -> Path:
        return self.project_root / "data" / ".pipeline-work" / self.run_id

    @property
    def raw_docx(self) -> Path:
        return self.project_root / "data" / "raw"

    @property
    def staging_data(self) -> Path:
        return self.workspace / "data"

    @property
    def staging_interim(self) -> Path:
        return self.staging_data / "interim"

    @property
    def staging_processed(self) -> Path:
        return self.staging_data / "processed"

    @property
    def staging_tables(self) -> Path:
        return self.staging_interim / "tables"

    @property
    def staging_parents(self) -> Path:
        return self.staging_processed / "chunks" / "parents.jsonl"

    @property
    def staging_children(self) -> Path:
        return self.staging_processed / "chunks" / "regex_constrained_semantic" / "chunks.jsonl"

    @property
    def staging_table_markdown(self) -> Path:
        return self.staging_processed / "tables_markdown"

    @property
    def staging_table_documents(self) -> Path:
        return self.staging_processed / "table_documents.jsonl"

    @property
    def staging_chroma(self) -> Path:
        return self.staging_processed / "chroma"

    @property
    def staging_bm25(self) -> Path:
        return self.staging_processed / "bm25"

    @property
    def staging_manifest(self) -> Path:
        return self.staging_processed / "metadata" / "source_manifest.json"

    @property
    def published_interim(self) -> Path:
        return self.project_root / "data" / "interim"

    @property
    def published_processed(self) -> Path:
        return self.project_root / "data" / "processed"

    @property
    def rollback_root(self) -> Path:
        # Fuera del workspace para que su limpieza nunca borre el respaldo
        return self.project_root / "data" / ".pipeline-backup" / self.run_id


@dataclass(frozen=True)
class StageOperations:
    """Reusable public functions invoked by the staged build."""

    ingest_docx: Callable[[Path, Path], list[Any]]
    clean_markdown: Callable[[Path, Path], None]
    write_parents: Callable[[Path, Path, Path, Path], Any]
    write_children: Callable[[Path, Path, Path], Any]
    audit_tables: Callable[[list[Any], Path], tuple[list[str], list[str]]]
    convert_tables: Callable[[Path, Path], list[Path]]
    write_table_documents: Callable[[Path, Path], int]
    ingest_chroma: Callable[[Path, Path, Path, int], Any]
    ingest_bm25: Callable[[Path, Path, Path], Any]
    validate_corpus: Callable[[Path, Path, Path, Path, Path], Any]


class OfflineBuildError(Exception):
    """Wrap a causal failure with the named offline build stage."""

    def __init__(self, stage: StageName, cause: BaseException, backup_path: Path | None = None) -> None:
        self.stage = stage
        self.cause = cause
        self.backup_path = backup_path
        super().__init__(f"{stage}: {cause}")


ProgressCallback = Callable[[StageEvent], None]


def run_stage(
    stage: StageName,
    number: int | None,
    operation: Callable[[], Any],
    progress_callback: ProgressCallback,
    describe: Callable[[Any], str] | None = None,
) -> StageResult:
    """Emit one start and terminal event for one stage operation."""

    progress_callback(StageEvent(stage, number, "started"))
    try:
        value = operation()
        detail = describe(value) if describe else ""
    except Exception as error:
        progress_callback(StageEvent(stage, number, "failed", str(error)))
        raise OfflineBuildError(stage, error) from error
    progress_callback(StageEvent(stage, number, "completed", detail))
    return StageResult(stage, value)


def build_offline_corpus(
    *,
    project_root: Path,
    operations: StageOperations,
    raw_docx_dir: Path | None = None,
    batch_size: int = 8,
    keep_workdir: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> list[StageResult]:
    """Build, validate, and publish the complete offline corpus.

    `project_root` and `operations` have no defaults so a caller never rebuilds the real corpus by omission.
    """

    if batch_size <= 0:
        raise ValueError("--batch-size must be greater than 0")
    callback = progress_callback or (lambda _event: None)
    paths = BuildPaths(project_root=project_root, run_id=uuid.uuid4().hex)
    source_raw_dir = raw_docx_dir or paths.raw_docx
    selected_operations = operations
    results: list[StageResult] = []
    try:
        run_stage(StageName.PREFLIGHT, None, lambda: _prepare_workspace(paths), callback)
        documents = run_stage(
            StageName.DOCX_INGESTION,
            1,
            lambda: _ingest_and_validate_documents(selected_operations, source_raw_dir, paths.staging_interim),
            callback,
            _document_detail,
        )
        results.append(documents)
        results.append(
            run_stage(
                StageName.MARKDOWN_CLEANUP,
                2,
                lambda: selected_operations.clean_markdown(paths.staging_interim, paths.staging_processed),
                callback,
                lambda _value: _require_cleaned_markdown(paths, documents.value),
            )
        )
        results.append(
            run_stage(
                StageName.PARENT_CHUNKING,
                3,
                lambda: selected_operations.write_parents(
                    paths.staging_processed,
                    paths.staging_parents,
                    paths.staging_manifest,
                    paths.staging_tables,
                ),
                callback,
                lambda value: _require_non_empty_output(paths.staging_parents, value),
            )
        )
        results.append(
            run_stage(
                StageName.REGEX_CHILD_CHUNKING,
                4,
                lambda: selected_operations.write_children(
                    paths.staging_parents,
                    paths.staging_children,
                    paths.staging_tables,
                ),
                callback,
                lambda value: _require_non_empty_output(paths.staging_children, value),
            )
        )
        results.append(
            run_stage(
                StageName.TABLE_REFERENCE_AUDIT,
                5,
                lambda: _audit_staged_tables(selected_operations, paths),
                callback,
                _audit_detail,
            )
        )
        results.append(
            run_stage(
                StageName.TABLE_MARKDOWN_CONVERSION,
                6,
                lambda: _convert_staged_tables(selected_operations, paths),
                callback,
                lambda converted: f"{len(converted)} table(s)",
            )
        )
        results.append(
            run_stage(
                StageName.TABLE_DOCUMENT_BUILD,
                7,
                lambda: selected_operations.write_table_documents(
                    paths.staging_table_markdown,
                    paths.staging_table_documents,
                ),
                callback,
                lambda count: _require_table_documents(paths.staging_table_documents, count),
            )
        )
        chroma = run_stage(
            StageName.CHROMA_INDEXING,
            8,
            lambda: _index_without_skips(
                selected_operations.ingest_chroma,
                paths.staging_children,
                paths.staging_table_documents,
                paths.staging_chroma,
                batch_size,
            ),
            callback,
            _index_detail,
        )
        results.append(chroma)
        bm25 = run_stage(
            StageName.BM25_INDEXING,
            9,
            lambda: _index_without_skips(
                selected_operations.ingest_bm25,
                paths.staging_children,
                paths.staging_table_documents,
                paths.staging_bm25,
            ),
            callback,
            _index_detail,
        )
        results.append(bm25)
        results.append(
            run_stage(
                StageName.CORPUS_VALIDATION,
                10,
                lambda: selected_operations.validate_corpus(
                    paths.staging_parents,
                    paths.staging_children,
                    paths.staging_table_documents,
                    paths.staging_chroma,
                    paths.staging_bm25,
                ),
                callback,
                lambda result: f"{result.source_record_count} records agree",
            )
        )
        _promote(paths, callback)
        return results
    finally:
        if not keep_workdir:
            shutil.rmtree(paths.workspace, ignore_errors=True)


def validate_published_corpus(project_root: Path = PROJECT_ROOT) -> Any:
    """Validate published artifacts without writing staging or indexes."""

    processed = project_root / "data" / "processed"
    return validate_corpus_artifacts(
        processed / "chunks" / "parents.jsonl",
        processed / "chunks" / "regex_constrained_semantic" / "chunks.jsonl",
        processed / "table_documents.jsonl",
        processed / "chroma",
        processed / "bm25",
    )


def default_stage_operations() -> StageOperations:
    """Load public stage functions only when a build starts."""

    from pipeline.cleaning.markdown_cleaner import clean_markdown_directory
    from pipeline.chunking.hierarchical_splitter.child_splitter.regex_constrained_semantic import (
        write_regex_constrained_semantic_child_output,
    )
    from pipeline.chunking.hierarchical_splitter.parent_builder import write_parent_chunk_output
    from pipeline.ingestion.docx_to_markdown import convert_docx_directory_to_markdown
    from pipeline.sparse_indexing.ingest import ingest_sparse_bm25_documents
    from pipeline.tables.table_documents import write_table_documents
    from pipeline.tables.table_markdown import convert_table_html_batch
    from pipeline.tables.table_references import audit_table_references
    from pipeline.vectorization.ingest import ingest_base_rag_documents

    return StageOperations(
        ingest_docx=convert_docx_directory_to_markdown,
        clean_markdown=clean_markdown_directory,
        write_parents=lambda source, output, manifest, tables: write_parent_chunk_output(
            source, output, manifest, tables
        ),
        write_children=lambda parents, output, tables: write_regex_constrained_semantic_child_output(
            parents,
            output,
            DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
            DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
            DEFAULT_EMBEDDING_MODEL,
            DEFAULT_MIN_TOKENS,
            DEFAULT_MAX_TOKENS,
            tables,
        ),
        audit_tables=audit_table_references,
        convert_tables=convert_table_html_batch,
        write_table_documents=write_table_documents,
        ingest_chroma=lambda children, tables, chroma, size: ingest_base_rag_documents(
            children, tables, chroma, batch_size=size
        ),
        ingest_bm25=ingest_sparse_bm25_documents,
        validate_corpus=validate_corpus_artifacts,
    )


def _prepare_workspace(paths: BuildPaths) -> None:
    backup_parent = paths.rollback_root.parent
    if backup_parent.is_dir() and any(backup_parent.iterdir()):
        raise FileExistsError(f"Unrestored publication backup found; restore it manually first: {backup_parent}")
    paths.staging_processed.mkdir(parents=True)
    published_metadata = paths.published_processed / "metadata"
    if published_metadata.is_dir():
        shutil.copytree(published_metadata, paths.staging_processed / "metadata")


def _raise_parsing_errors(documents: list[Any]) -> None:
    errors = [error for document in documents for error in getattr(document, "parsing_errors", [])]
    if errors:
        raise ValueError("; ".join(errors))


def _ingest_and_validate_documents(
    operations: StageOperations,
    raw_docx: Path,
    staging_interim: Path,
) -> list[Any]:
    documents = operations.ingest_docx(raw_docx, staging_interim)
    _raise_parsing_errors(documents)
    return documents


def _require_cleaned_markdown(paths: BuildPaths, documents: list[Any]) -> str:
    expected = len(documents)
    actual = len(list(paths.staging_processed.glob("*.md")))
    if actual != expected:
        raise ValueError(f"Expected {expected} cleaned Markdown document(s), found {actual}")
    return f"{actual} document(s)"


def _require_non_empty_output(path: Path, result: Any) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Required artifact is empty: {path}")
    return f"{getattr(result, 'chunk_count', 'artifact')} record(s)"


def _audit_staged_tables(operations: StageOperations, paths: BuildPaths) -> tuple[list[str], list[str]]:
    chunks = [*read_jsonl(paths.staging_parents), *read_jsonl(paths.staging_children)]
    missing, orphaned = operations.audit_tables(chunks, paths.staging_tables)
    if missing:
        raise ValueError(f"Missing referenced table files: {', '.join(missing)}")
    return missing, orphaned


def _audit_detail(result: tuple[list[str], list[str]]) -> str:
    return f"{len(result[1])} orphaned table warning(s)" if result[1] else "references valid"


def _convert_staged_tables(operations: StageOperations, paths: BuildPaths) -> list[Path]:
    converted = operations.convert_tables(paths.staging_tables, paths.staging_table_markdown)
    table_count = len(list(paths.staging_tables.glob("*/table_*.html")))
    if len(converted) != table_count:
        raise ValueError(f"Expected {table_count} table Markdown file(s), converted {len(converted)}")
    return converted


def _require_table_documents(path: Path, count: int) -> str:
    if not path.is_file():
        raise ValueError(f"Missing table documents artifact: {path}")
    return f"{count} table document(s)"


def _reject_skipped_records(result: Any) -> None:
    skipped = getattr(result, "skipped_count", 0)
    if skipped:
        raise ValueError(f"Skipped source records: {skipped}")


def _index_without_skips(
    operation: Callable[..., Any],
    children: Path,
    tables: Path,
    destination: Path,
    batch_size: int | None = None,
) -> Any:
    result = (
        operation(children, tables, destination, batch_size)
        if batch_size is not None
        else operation(children, tables, destination)
    )
    _reject_skipped_records(result)
    return result


def _document_detail(documents: list[Any]) -> str:
    table_count = sum(len(getattr(document, "tables", [])) for document in documents)
    return f"{len(documents)} document(s), {table_count} extracted table(s)"


def _index_detail(result: Any) -> str:
    return f"{getattr(result, 'total_count', 0)} record(s)"


def _managed_entries(data_root: Path) -> list[Path]:
    """Return existing managed entries under one data root, relative to that root."""

    entries: list[Path] = []
    for area, managed in MANAGED_ENTRIES.items():
        area_root = data_root / area
        # Los *.md de primer nivel se reemplazan como conjunto para no dejar fuentes obsoletas
        entries.extend(path.relative_to(data_root) for path in sorted(area_root.glob("*.md")))
        entries.extend(Path(area, entry) for entry in managed if (area_root / entry).exists())
    return entries


def _move_entry(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def _remove_entry(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _restore_backup(paths: BuildPaths, backed_up: list[Path], attempted: list[Path]) -> None:
    published_data = paths.project_root / "data"
    for relative in reversed(attempted):
        _remove_entry(published_data / relative)
    for relative in reversed(backed_up):
        _move_entry(paths.rollback_root / relative, published_data / relative)
    shutil.rmtree(paths.rollback_root, ignore_errors=True)


def _promote(paths: BuildPaths, callback: ProgressCallback) -> None:
    callback(StageEvent(StageName.PUBLICATION, None, "started"))
    published_data = paths.project_root / "data"
    backed_up: list[Path] = []
    attempted: list[Path] = []
    try:
        for relative in _managed_entries(published_data):
            _move_entry(published_data / relative, paths.rollback_root / relative)
            backed_up.append(relative)
        for relative in _managed_entries(paths.staging_data):
            attempted.append(relative)
            _move_entry(paths.staging_data / relative, published_data / relative)
    except BaseException as error:
        callback(StageEvent(StageName.PUBLICATION, None, "failed", str(error)))
        try:
            _restore_backup(paths, backed_up, attempted)
        except BaseException as restore_error:
            raise OfflineBuildError(StageName.PUBLICATION, restore_error, paths.rollback_root) from error
        if isinstance(error, Exception):
            raise OfflineBuildError(StageName.PUBLICATION, error) from error
        raise
    try:
        shutil.rmtree(paths.rollback_root)
        paths.rollback_root.parent.rmdir()
    except FileNotFoundError:
        pass
    except OSError as error:
        callback(StageEvent(StageName.PUBLICATION, None, "warning", f"Backup cleanup failed: {error}"))
    callback(StageEvent(StageName.PUBLICATION, None, "completed"))
