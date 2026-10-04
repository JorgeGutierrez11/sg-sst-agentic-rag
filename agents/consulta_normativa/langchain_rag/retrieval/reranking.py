"""Post-retrieval document reranking helpers."""

from collections.abc import Callable
from functools import lru_cache
import logging
from math import ceil
from time import perf_counter
from typing import Any

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument

logger = logging.getLogger(__name__)

RERANKING_METADATA_FIELDS = (
    ("Fuente", "source_stem"),
    ("Tipo normativo", "normative_document_type"),
    ("Año", "year"),
    ("Título", "title"),
    ("Capítulo", "chapter"),
    ("Artículo", "article"),
    ("Parágrafo", "paragraph"),
    ("Numeral", "numeral"),
    ("Literal", "literal"),
    ("Tipo de fragmento", "document_type"),
    ("Tabla", "table_key"),
    ("Tablas relacionadas", "table_keys"),
)


@lru_cache(maxsize=4)
def get_reranker(model_name: str, max_length: int, device: str) -> Any:
    """Load and cache a CrossEncoder reranker lazily."""

    # pyrefly: ignore [missing-import]
    from sentence_transformers import CrossEncoder

    return CrossEncoder(
        model_name,
        max_length=max_length,
        device=device,
    )


def rerank_node(
    reranker: Any,
    candidate_pool_size: int,
    final_top_k: int,
    *,
    batch_size: int = 32,
    device: str = "cpu",
    input_max_length: int = 512,
) -> Callable[[RagGraphState], RagGraphState]:
    """Rerank state documents and write the selected documents back to state documents."""

    def run(state: RagGraphState) -> RagGraphState:
        started_at = perf_counter()
        documents = state.get("documents", [])
        candidate_documents = documents[:candidate_pool_size]
        query = state["question"]

        if not candidate_documents:
            candidate_count = len(candidate_documents)
            selected_count = 0
            batch_count = ceil(candidate_count / batch_size) if candidate_count else 0
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            trace = {
                "fallback": False,
                "candidate_count": candidate_count,
                "selected_count": selected_count,
                "duration_ms": duration_ms,
                "batch_count": batch_count,
                "device": device,
                "input_max_length": input_max_length,
            }
            logger.info(
                "CrossEncoder rerank completed | duration_ms=%s | candidate_count=%s | "
                "selected_count=%s | batch_count=%s | device=%s | input_max_length=%s | fallback=%s",
                duration_ms,
                candidate_count,
                selected_count,
                batch_count,
                device,
                input_max_length,
                False,
            )
            return {
                "documents": [],
                "reranking_trace": trace,
            }

        try:
            selected_documents = rerank_documents(
                query,
                candidate_documents,
                resolve_reranker(reranker),
                final_top_k,
                batch_size=batch_size,
            )
            candidate_count = len(candidate_documents)
            selected_count = len(selected_documents)
            batch_count = ceil(candidate_count / batch_size) if candidate_count else 0
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            trace = {
                "fallback": False,
                "candidate_count": candidate_count,
                "selected_count": selected_count,
                "duration_ms": duration_ms,
                "batch_count": batch_count,
                "device": device,
                "input_max_length": input_max_length,
            }
            logger.info(
                "CrossEncoder rerank completed | duration_ms=%s | candidate_count=%s | "
                "selected_count=%s | batch_count=%s | device=%s | input_max_length=%s | fallback=%s",
                duration_ms,
                candidate_count,
                selected_count,
                batch_count,
                device,
                input_max_length,
                False,
            )
            return {
                "documents": selected_documents,
                "reranking_trace": trace,
            }
        except Exception as error:  # pragma: no cover - exact dependency failures vary by environment.
            fallback_update = fallback_reranking_update(
                candidate_documents,
                final_top_k,
                error,
            )
            selected_documents = fallback_update["documents"]
            candidate_count = len(candidate_documents)
            selected_count = len(selected_documents)
            batch_count = ceil(candidate_count / batch_size) if candidate_count else 0
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            fallback_update["reranking_trace"].update(
                {
                    "duration_ms": duration_ms,
                    "batch_count": batch_count,
                    "device": device,
                    "input_max_length": input_max_length,
                }
            )
            logger.warning(
                "CrossEncoder rerank fallback | duration_ms=%s | candidate_count=%s | "
                "selected_count=%s | batch_count=%s | device=%s | input_max_length=%s | fallback=%s",
                duration_ms,
                candidate_count,
                selected_count,
                batch_count,
                device,
                input_max_length,
                True,
            )
            return fallback_update

    return run


def rerank_documents(
    query: str,
    documents: list[RetrievedDocument],
    reranker: Any,
    final_top_k: int,
    *,
    batch_size: int = 32,
) -> list[RetrievedDocument]:
    """Score query/document pairs and return the top documents by descending score."""

    candidate_pairs = [(query, document_text_for_reranking(document)) for document in documents]
    scores = reranker.predict(
        candidate_pairs,
        batch_size=batch_size,
        show_progress_bar=False,
    )
    ranked_documents = sorted(
        zip(documents, scores, strict=False),
        key=lambda item: item[1],
        reverse=True,
    )
    return [document for document, _score in ranked_documents[:final_top_k]]


def document_text_for_reranking(document: RetrievedDocument) -> str:
    """Return compact metadata plus text sent to the reranker for one candidate."""

    metadata_text = compact_normative_metadata_text(document.metadata, RERANKING_METADATA_FIELDS)
    if not metadata_text:
        return document.document
    return f"Metadata normativa:\n{metadata_text}\n\nContenido:\n{document.document}"


def compact_normative_metadata_text(
    metadata: dict[str, Any],
    fields: tuple[tuple[str, str], ...],
) -> str:
    """Return only compact legal locator metadata; never trace/debug metadata."""

    lines: list[str] = []
    for label, key in fields:
        value = metadata.get(key)
        formatted = format_metadata_value(value)
        if formatted:
            lines.append(f"{label}: {formatted}")
    return "\n".join(lines)


def format_metadata_value(value: object) -> str:
    """Format scalar or list metadata values for retrieval scoring text."""

    if value in (None, ""):
        return ""
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(items)
    return str(value).strip()


def resolve_reranker(reranker: Any) -> Any:
    """Resolve a reranker instance or lazy loader."""

    if callable(reranker) and not hasattr(reranker, "predict"):
        return reranker()
    return reranker


def fallback_reranking_update(
    documents: list[RetrievedDocument],
    final_top_k: int,
    error: Exception,
) -> RagGraphState:
    """Return conservative reranking fallback state update."""

    selected_documents = documents[:final_top_k]
    return {
        "documents": selected_documents,
        "reranking_trace": {
            "fallback": True,
            "error": type(error).__name__,
            "candidate_count": len(documents),
            "selected_count": len(selected_documents),
        },
    }
