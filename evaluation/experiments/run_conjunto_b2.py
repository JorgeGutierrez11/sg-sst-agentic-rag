"""Run conversational Conjunto B2 against the current business-context technique."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

DEFAULT_DATASET = Path(
    "evaluation/datasets/conjunto_b_optim/conjunto_b2_queries.json"
)
FIELDNAMES = ["Query", "Document", "Answer"]
ID_PATTERN = re.compile(r"^B2-(T\d+)-Q(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta Conjunto B2 conservando memoria dentro de cada hilo y "
            "aislando los hilos entre sí. Exporta Query, Document y Answer."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Dataset JSON. Default: {DEFAULT_DATASET}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="TSV de salida, por ejemplo evaluation/results/ares_runs/full_conversation_memory.tsv",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina el TSV existente y ejecuta los 8 hilos desde cero.",
    )
    return parser.parse_args()


def parse_id(record_id: str) -> tuple[str, int]:
    match = ID_PATTERN.fullmatch(record_id)
    if match is None:
        raise ValueError(
            f"ID inválido {record_id!r}. Formato esperado: B2-T01-Q01."
        )
    return match.group(1), int(match.group(2))


def load_dataset(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list) or not data:
        raise ValueError("El dataset debe ser una lista JSON no vacía.")

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_queries: set[str] = set()

    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Registro {index}: se esperaba un objeto JSON.")

        record_id = item.get("ID")
        query = item.get("Query")

        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"Registro {index}: ID inválido.")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Registro {record_id}: Query inválida.")
        if record_id in seen_ids:
            raise ValueError(f"ID duplicado: {record_id}")
        thread_name, turn = parse_id(record_id)
        seen_ids.add(record_id)
        seen_queries.add(query)
        rows.append(
            {
                "ID": record_id,
                "Query": query,
                "thread": thread_name,
                "turn": turn,
            }
        )

    validate_threads(rows)
    return rows


def validate_threads(rows: list[dict[str, Any]]) -> None:
    grouped: OrderedDict[str, list[int]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["thread"], []).append(row["turn"])

    for thread_name, turns in grouped.items():
        expected = list(range(1, len(turns) + 1))
        if turns != expected:
            raise ValueError(
                f"{thread_name}: los turnos deben estar ordenados y ser consecutivos. "
                f"Encontrado={turns}, esperado={expected}."
            )


def read_existing_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if reader.fieldnames != FIELDNAMES:
            raise ValueError(
                f"El TSV existente debe tener exactamente estas columnas: {FIELDNAMES}"
            )
        return [dict(row) for row in reader]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            delimiter="\t",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)
        file.flush()
        os.fsync(file.fileno())


def append_result(path: Path, *, query: str, document: str, answer: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            delimiter="\t",
            quoting=csv.QUOTE_MINIMAL,
        )
        if needs_header:
            writer.writeheader()
        writer.writerow(
            {
                "Query": query,
                "Document": document,
                "Answer": answer,
            }
        )
        file.flush()
        os.fsync(file.fileno())


def group_dataset(rows: list[dict[str, Any]]) -> OrderedDict[str, list[dict[str, Any]]]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["thread"], []).append(row)
    return grouped


def normalize_existing_output(
    output: Path,
    dataset: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], set[str]]:
    """Keep complete threads and discard a partial final thread before resuming.

    The ARES TSV intentionally has no ID column, and B2 may contain repeated
    query text in different threads. Resume is therefore positional: existing
    TSV rows must match the dataset in exactly the same order.

    B2 cannot safely resume in the middle of a conversation with a fresh
    in-memory checkpointer/store. If the final stored thread is incomplete,
    all rows from that thread are removed and it is executed again from Q01.
    """

    existing_rows = read_existing_rows(output)
    if not existing_rows:
        return [], set()

    if len(existing_rows) > len(dataset):
        raise ValueError(
            "El TSV tiene más filas que el dataset. Usa otro --output o --reset."
        )

    for index, existing in enumerate(existing_rows):
        expected_query = dataset[index]["Query"]
        if existing.get("Query") != expected_query:
            raise ValueError(
                "El TSV existente no corresponde al dataset actual en la fila "
                f"{index + 1}. Usa otro --output o ejecuta con --reset."
            )

    grouped = group_dataset(dataset)
    complete_threads: set[str] = set()
    offset = 0
    truncate_at: int | None = None
    partial_thread: str | None = None

    for thread_name, thread_rows in grouped.items():
        thread_end = offset + len(thread_rows)

        if len(existing_rows) >= thread_end:
            complete_threads.add(thread_name)
            offset = thread_end
            continue

        if len(existing_rows) > offset:
            partial_thread = thread_name
            truncate_at = offset
        break

    if partial_thread is not None and truncate_at is not None:
        print(
            f"Hilo incompleto detectado: {partial_thread}. "
            "Se eliminará del TSV y se repetirá completo."
        )
        existing_rows = existing_rows[:truncate_at]
        write_rows(output, existing_rows)

    return existing_rows, complete_threads


def state_values(graph: Any, thread_id: str) -> dict[str, Any]:
    snapshot = graph.get_state(
        {"configurable": {"thread_id": thread_id}}
    )
    values = getattr(snapshot, "values", None)
    return values if isinstance(values, dict) else {}


def build_document(result: Any, values: dict[str, Any], record_id: str) -> str:
    normative_context = getattr(result, "context", None)
    if not isinstance(normative_context, str) or not normative_context.strip():
        raise ValueError(f"{record_id}: el RAG no produjo contexto normativo válido.")

    business_context = values.get("business_context", {})
    current_context = ""
    if isinstance(business_context, dict):
        raw_current_context = business_context.get("current_context", "")
        if isinstance(raw_current_context, str):
            current_context = raw_current_context.strip()

    # Para ARES se exporta un solo Document. En B2 ese Document reúne el
    # contexto empresarial producido por la técnica y el contexto normativo
    # recuperado. Si la técnica no produjo current_context, solo se exporta
    # el contexto normativo.
    sections: list[str] = []
    if current_context:
        sections.append(f"CONTEXTO EMPRESARIAL\n{current_context}")
    sections.append(f"CONTEXTO NORMATIVO RECUPERADO\n{normative_context.strip()}")
    return "\n\n".join(sections)


def validate_answer(result: Any, record_id: str) -> str:
    answer = getattr(result, "answer", None)
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"{record_id}: el RAG no produjo una Answer válida.")
    return answer


def main() -> int:
    args = parse_args()
    dataset = load_dataset(args.dataset)

    if args.reset and args.output.exists():
        args.output.unlink()

    _, complete_threads = normalize_existing_output(args.output, dataset)
    grouped = group_dataset(dataset)

    print(f"Dataset: {args.dataset}")
    print(f"Salida: {args.output}")
    print(
        f"Hilos: {len(grouped)} | Completos: {len(complete_threads)} | "
        f"Pendientes: {len(grouped) - len(complete_threads)}"
    )

    if len(complete_threads) == len(grouped):
        print("No hay hilos pendientes.")
        return 0

    # Un solo runtime para toda la corrida. Cada Txx usa un thread_id propio:
    # dentro del hilo se conserva memoria; entre hilos el estado queda aislado.
    from agents.consulta_normativa.langchain_rag.main import build_runtime

    runtime = build_runtime()
    run_id = uuid4().hex[:12]

    for thread_index, (thread_name, thread_rows) in enumerate(grouped.items(), start=1):
        if thread_name in complete_threads:
            print(f"[{thread_index:02d}/{len(grouped)}] {thread_name} - completo, se omite")
            continue

        thread_id = f"b2-{run_id}-{thread_name}"
        print(f"[{thread_index:02d}/{len(grouped)}] {thread_name} - iniciando hilo")

        for row in thread_rows:
            record_id = row["ID"]
            query = row["Query"]
            turn = row["turn"]
            print(f"  [{turn:02d}/{len(thread_rows)}] {record_id} - ejecutando")

            # Las 10 consultas del hilo comparten el mismo thread_id.
            # Si una falla, la corrida se detiene. Al reanudar, este hilo
            # incompleto será eliminado del TSV y ejecutado nuevamente entero.
            result = runtime.answer_with_langgraph(
                query,
                runtime.graph,
                thread_id=thread_id,
            )
            values = state_values(runtime.graph, thread_id)
            document = build_document(result, values, record_id)
            answer = validate_answer(result, record_id)

            append_result(
                args.output,
                query=query,
                document=document,
                answer=answer,
            )
            print(f"  [{turn:02d}/{len(thread_rows)}] {record_id} - guardada")

        print(f"[{thread_index:02d}/{len(grouped)}] {thread_name} - hilo completo")

    print(f"Completado: {len(dataset)}/{len(dataset)} consultas")
    print(f"TSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
