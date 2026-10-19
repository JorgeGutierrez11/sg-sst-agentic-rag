import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline import offline_orchestration
from pipeline.offline_orchestration import (
    STAGE_ORDER,
    OfflineBuildError,
    StageName,
    StageOperations,
    build_offline_corpus,
    run_stage,
)

UNMANAGED_FILES = {
    "processed/chunks/sliding_window/chunks.jsonl": "baseline",
    "processed/chunks/semantic_chunking/chunks.jsonl": "semantic baseline",
    "processed/chunks/comparison/report.json": "{}",
    "processed/tables_htlm/norma/table_0.html": "<table></table>",
    "processed/metadata/source_manifest.json": "{}",
}

PUBLISHED_MANAGED_FILES = {
    "interim/Stale.md": "stale interim",
    "interim/Norma.md": "old interim",
    "interim/tables/Norma/table_0.html": "<table>old</table>",
    "processed/Stale.md": "stale cleaned",
    "processed/Norma.md": "old cleaned",
    "processed/chunks/parents.jsonl": "old parents\n",
    "processed/chunks/regex_constrained_semantic/chunks.jsonl": "old children\n",
    "processed/tables_markdown/Norma/table_0.md": "old table",
    "processed/table_documents.jsonl": "old tables\n",
    "processed/chroma/chroma.sqlite3": "old chroma",
    "processed/bm25/corpus.jsonl": "old bm25\n",
}


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def snapshot(root: Path) -> dict[str, str]:
    """Return published data files, excluding build and backup scratch."""

    data = root / "data"
    if not data.is_dir():
        return {}
    return {
        path.relative_to(data).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(data.rglob("*"))
        if path.is_file() and path.relative_to(data).parts[0] not in {".pipeline-work", ".pipeline-backup"}
    }


class FakeStages:
    """Fake stage operations writing minimal artifacts and recording received paths."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.published_at_validation: dict[str, str] | None = None

    def record(self, name: str, *args: object) -> None:
        self.calls.append((name, args))

    def ingest_docx(self, raw: Path, output: Path) -> list[object]:
        self.record("ingest_docx", output)
        write_file(output / "Norma.md", "new interim")
        write_file(output / "tables" / "Norma" / "table_0.html", "<table>new</table>")
        return [SimpleNamespace(parsing_errors=[], tables=["table_0"])]

    def clean_markdown(self, source: Path, output: Path) -> None:
        self.record("clean_markdown", source, output)
        write_file(output / "Norma.md", "new cleaned")

    def write_parents(self, source: Path, output: Path, manifest: Path, tables: Path) -> object:
        self.record("write_parents", source, output, manifest, tables)
        write_file(output, json.dumps({"chunk_id": "parent-1"}) + "\n")
        return SimpleNamespace(chunk_count=1)

    def write_children(self, parents: Path, output: Path, tables: Path) -> object:
        self.record("write_children", parents, output, tables)
        write_file(output, json.dumps({"chunk_id": "child-1", "parent_id": "parent-1"}) + "\n")
        return SimpleNamespace(chunk_count=1)

    def audit_tables(self, chunks: list[object], tables: Path) -> tuple[list[str], list[str]]:
        self.record("audit_tables", tables)
        return [], []

    def convert_tables(self, tables: Path, output: Path) -> list[Path]:
        self.record("convert_tables", tables, output)
        converted = output / "Norma" / "table_0.md"
        write_file(converted, "new table")
        return [converted]

    def write_table_documents(self, markdown: Path, output: Path) -> int:
        self.record("write_table_documents", markdown, output)
        write_file(output, json.dumps({"id": "table-1"}) + "\n")
        return 1

    def ingest_chroma(self, children: Path, tables: Path, chroma: Path, batch_size: int) -> object:
        self.record("ingest_chroma", children, tables, chroma)
        write_file(chroma / "chroma.sqlite3", "new chroma")
        return SimpleNamespace(skipped_count=0, total_count=2)

    def ingest_bm25(self, children: Path, tables: Path, bm25: Path) -> object:
        self.record("ingest_bm25", children, tables, bm25)
        write_file(bm25 / "corpus.jsonl", "new bm25\n")
        return SimpleNamespace(skipped_count=0, total_count=2)

    def validate_corpus(self, *paths: Path) -> object:
        self.record("validate_corpus", *paths)
        self.published_at_validation = snapshot(self.root)
        return SimpleNamespace(parent_count=1, source_record_count=2)

    def operations(self) -> StageOperations:
        return StageOperations(
            ingest_docx=self.ingest_docx,
            clean_markdown=self.clean_markdown,
            write_parents=self.write_parents,
            write_children=self.write_children,
            audit_tables=self.audit_tables,
            convert_tables=self.convert_tables,
            write_table_documents=self.write_table_documents,
            ingest_chroma=self.ingest_chroma,
            ingest_bm25=self.ingest_bm25,
            validate_corpus=self.validate_corpus,
        )


class OfflineOrchestrationTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.events: list[object] = []
        self.stages = FakeStages(self.root)

    def publish_existing_corpus(self) -> dict[str, str]:
        for relative, content in {**UNMANAGED_FILES, **PUBLISHED_MANAGED_FILES}.items():
            write_file(self.root / "data" / relative, content)
        return snapshot(self.root)

    def build(self, operations: StageOperations | None = None, **kwargs: object) -> list[object]:
        return build_offline_corpus(
            project_root=self.root,
            operations=operations or self.stages.operations(),
            progress_callback=self.events.append,
            **kwargs,
        )

    def statuses(self) -> list[tuple[str, str]]:
        return [(str(event.stage), event.status) for event in self.events]

    def test_stage_runner_emits_one_lifecycle_pair_on_success(self) -> None:
        events = []

        result = run_stage(StageName.DOCX_INGESTION, 1, lambda: "done", events.append)

        self.assertEqual(result.value, "done")
        self.assertEqual([event.status for event in events], ["started", "completed"])
        self.assertTrue(all(event.stage is StageName.DOCX_INGESTION for event in events))

    def test_stage_runner_wraps_the_causal_error_and_emits_failed(self) -> None:
        events = []

        with self.assertRaises(OfflineBuildError) as context:
            run_stage(
                StageName.MARKDOWN_CLEANUP,
                2,
                lambda: (_ for _ in ()).throw(ValueError("cleanup broke")),
                events.append,
            )

        self.assertEqual(context.exception.stage, StageName.MARKDOWN_CLEANUP)
        self.assertIsInstance(context.exception.__cause__, ValueError)
        self.assertEqual([event.status for event in events], ["started", "failed"])

    def test_build_requires_explicit_project_root_and_operations(self) -> None:
        with self.assertRaises(TypeError):
            build_offline_corpus(project_root=self.root)  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            build_offline_corpus(operations=self.stages.operations())  # type: ignore[call-arg]

    def test_parsing_errors_fail_the_docx_stage_before_cleanup(self) -> None:
        failing = replace(
            self.stages.operations(),
            ingest_docx=lambda _raw, _output: [SimpleNamespace(parsing_errors=["Pandoc failed"], tables=[])],
            clean_markdown=self.fail,
        )

        with self.assertRaises(OfflineBuildError) as context:
            self.build(failing)

        self.assertEqual(context.exception.stage, StageName.DOCX_INGESTION)
        self.assertEqual(self.statuses()[-2:], [("docx_ingestion", "started"), ("docx_ingestion", "failed")])

    def test_build_runs_the_ten_stages_in_order_against_staging_paths_only(self) -> None:
        before = self.publish_existing_corpus()

        self.build()

        completed = [stage for stage, status in self.statuses() if status == "completed"]
        self.assertEqual(completed, ["preflight", *map(str, STAGE_ORDER), "publication"])
        self.assertEqual(
            [event.number for event in self.events if event.status == "completed"],
            [None, *range(1, 11), None],
        )
        workspace_root = self.root / "data" / ".pipeline-work"
        received = [arg for name, args in self.stages.calls for arg in args if isinstance(arg, Path)]
        self.assertTrue(received)
        for path in received:
            self.assertTrue(path.is_relative_to(workspace_root), path)
        self.assertEqual(self.stages.published_at_validation, before)

    def test_successful_build_publishes_only_managed_entries(self) -> None:
        self.publish_existing_corpus()

        self.build()

        after = snapshot(self.root)
        for relative, content in UNMANAGED_FILES.items():
            self.assertEqual(after[relative], content, relative)
        self.assertNotIn("interim/Stale.md", after)
        self.assertNotIn("processed/Stale.md", after)
        self.assertEqual(after["interim/Norma.md"], "new interim")
        self.assertEqual(after["interim/tables/Norma/table_0.html"], "<table>new</table>")
        self.assertEqual(after["processed/Norma.md"], "new cleaned")
        self.assertEqual(after["processed/chroma/chroma.sqlite3"], "new chroma")
        self.assertEqual(after["processed/bm25/corpus.jsonl"], "new bm25\n")
        self.assertEqual(after["processed/tables_markdown/Norma/table_0.md"], "new table")
        self.assertFalse((self.root / "data" / ".pipeline-backup").exists())
        self.assertEqual(list((self.root / "data" / ".pipeline-work").iterdir()), [])

    def test_validation_failure_does_not_publish(self) -> None:
        before = self.publish_existing_corpus()
        failing = replace(self.stages.operations(), validate_corpus=self.raise_value_error)

        with self.assertRaises(OfflineBuildError) as context:
            self.build(failing)

        self.assertEqual(context.exception.stage, StageName.CORPUS_VALIDATION)
        self.assertEqual(snapshot(self.root), before)
        self.assertNotIn("publication", [stage for stage, _status in self.statuses()])

    def test_failed_promotion_restores_the_previous_corpus(self) -> None:
        before = self.publish_existing_corpus()

        with patch.object(offline_orchestration, "_move_entry", self.failing_move(OSError("disk full"))):
            with self.assertRaises(OfflineBuildError) as context:
                self.build()

        self.assertEqual(context.exception.stage, StageName.PUBLICATION)
        self.assertIsNone(context.exception.backup_path)
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse(any((self.root / "data" / ".pipeline-backup").glob("*")))
        self.assertIn(("publication", "failed"), self.statuses())

    def test_interrupted_promotion_restores_the_previous_corpus(self) -> None:
        before = self.publish_existing_corpus()

        with patch.object(offline_orchestration, "_move_entry", self.failing_move(KeyboardInterrupt())):
            with self.assertRaises(KeyboardInterrupt):
                self.build()

        self.assertEqual(snapshot(self.root), before)

    def test_failed_restore_retains_the_backup_outside_the_workspace(self) -> None:
        self.publish_existing_corpus()

        with patch.object(
            offline_orchestration,
            "_move_entry",
            self.failing_move(OSError("disk full"), fail_restore=True),
        ):
            with self.assertRaises(OfflineBuildError) as context:
                self.build()

        backup = context.exception.backup_path
        self.assertIsNotNone(backup)
        self.assertTrue((backup / "processed" / "chroma" / "chroma.sqlite3").is_file())
        self.assertEqual(list((self.root / "data" / ".pipeline-work").iterdir()), [])

    def test_unrestored_backup_blocks_a_new_build_in_preflight(self) -> None:
        write_file(self.root / "data" / ".pipeline-backup" / "old-run" / "processed" / "x.md", "kept")

        with self.assertRaises(OfflineBuildError) as context:
            self.build()

        self.assertEqual(context.exception.stage, StageName.PREFLIGHT)
        self.assertEqual(self.stages.calls, [])

    def test_keep_workdir_retains_the_staging_workspace(self) -> None:
        self.build(keep_workdir=True)

        self.assertEqual(len(list((self.root / "data" / ".pipeline-work").iterdir())), 1)

    def test_missing_referenced_tables_fail_the_audit_stage(self) -> None:
        failing = replace(
            self.stages.operations(),
            audit_tables=lambda _chunks, _tables: (["Norma/table_9"], []),
            convert_tables=self.fail,
        )

        with self.assertRaises(OfflineBuildError) as context:
            self.build(failing)

        self.assertEqual(context.exception.stage, StageName.TABLE_REFERENCE_AUDIT)
        self.assertIn("Norma/table_9", str(context.exception.cause))

    def test_orphaned_tables_only_warn(self) -> None:
        warning = replace(
            self.stages.operations(),
            audit_tables=lambda _chunks, _tables: ([], ["Norma/table_7"]),
        )

        self.build(warning)

        audit = [event for event in self.events if event.stage is StageName.TABLE_REFERENCE_AUDIT][-1]
        self.assertEqual((audit.status, audit.detail), ("completed", "1 orphaned table warning(s)"))

    def test_empty_parent_output_fails_the_parent_stage(self) -> None:
        failing = replace(
            self.stages.operations(),
            write_parents=lambda _source, output, _manifest, _tables: write_file(output, ""),
            write_children=self.fail,
        )

        with self.assertRaises(OfflineBuildError) as context:
            self.build(failing)

        self.assertEqual(context.exception.stage, StageName.PARENT_CHUNKING)

    def test_skipped_records_fail_the_index_stage(self) -> None:
        for field, stage in (("ingest_chroma", StageName.CHROMA_INDEXING), ("ingest_bm25", StageName.BM25_INDEXING)):
            with self.subTest(stage=stage):
                failing = replace(
                    self.stages.operations(),
                    **{field: lambda *_args: SimpleNamespace(skipped_count=3, total_count=1)},
                )

                with self.assertRaises(OfflineBuildError) as context:
                    self.build(failing)

                self.assertEqual(context.exception.stage, stage)
                self.assertIn("Skipped source records: 3", str(context.exception.cause))

    def failing_move(self, error: BaseException, fail_restore: bool = False):
        """Fail the second staged promotion, and optionally every backup restore."""

        real_move = offline_orchestration._move_entry
        workspace_root = self.root / "data" / ".pipeline-work"
        backup_root = self.root / "data" / ".pipeline-backup"
        promotions = 0

        def move(source: Path, destination: Path) -> None:
            nonlocal promotions
            if source.is_relative_to(workspace_root):
                promotions += 1
                if promotions == 2:
                    raise error
            if fail_restore and source.is_relative_to(backup_root):
                raise OSError("restore failed")
            real_move(source, destination)

        return move

    @staticmethod
    def raise_value_error(*_args: object) -> object:
        raise ValueError("Index ID mismatch")

    @staticmethod
    def fail(*_args: object) -> object:
        raise AssertionError("later stage must not execute")


if __name__ == "__main__":
    unittest.main()
