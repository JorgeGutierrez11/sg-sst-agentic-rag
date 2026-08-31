"""Run Conjunto B1 against the currently configured RAG graph and export ARES TSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

DEFAULT_DATASET = Path(
    "evaluation/datasets/conjunto_b_optim/conjunto_b1_queries.json"
)
FIELDNAMES = ["Query", "Document", "Answer"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta Conjunto B1 como consultas independientes y guarda "
            "Query, Document y Answer en un TSV compatible con ARES."
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
        help="TSV de salida, por ejemplo evaluation/results/ares_runs/query_rewriting.tsv",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Elimina el TSV existente y ejecuta las 80 preguntas desde cero.",
    )
    return parser.parse_args()


def load_dataset(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list) or not data:
        raise ValueError("El dataset debe ser una lista JSON no vacía.")

    rows: list[dict[str, str]] = []
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
        if query in seen_queries:
            raise ValueError(
                f"Query duplicada en B1; no se puede reanudar de forma segura: {query!r}"
            )

        seen_ids.add(record_id)
        seen_queries.add(query)
        rows.append({"ID": record_id, "Query": query})

    return rows


def load_completed_queries(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if reader.fieldnames != FIELDNAMES:
            raise ValueError(
                f"El TSV existente debe tener exactamente estas columnas: {FIELDNAMES}"
            )
        return {row["Query"] for row in reader if row.get("Query")}


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


def validate_result(result: Any, record_id: str) -> tuple[str, str]:
    document = getattr(result, "context", None)
    answer = getattr(result, "answer", None)

    if not isinstance(document, str) or not document.strip():
        raise ValueError(f"{record_id}: el RAG no produjo un Document/context válido.")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"{record_id}: el RAG no produjo una Answer válida.")

    return document, answer


def main() -> int:
    args = parse_args()
    dataset = load_dataset(args.dataset)

    if args.reset and args.output.exists():
        args.output.unlink()

    completed_queries = load_completed_queries(args.output)
    dataset_queries = {row["Query"] for row in dataset}
    unknown_queries = completed_queries - dataset_queries
    if unknown_queries:
        raise ValueError(
            "El TSV de salida contiene queries que no pertenecen al dataset actual. "
            "Usa otro --output o ejecuta con --reset."
        )

    pending = [row for row in dataset if row["Query"] not in completed_queries]

    print(f"Dataset: {args.dataset}")
    print(f"Salida: {args.output}")
    print(f"Total: {len(dataset)} | Completadas: {len(completed_queries)} | Pendientes: {len(pending)}")

    if not pending:
        print("No hay consultas pendientes.")
        return 0

    # El runtime se construye UNA sola vez. Cada query usa un thread_id distinto,
    # por lo que B1 no arrastra estado conversacional entre preguntas.
    from agents.consulta_normativa.langchain_rag.main import build_runtime

    runtime = build_runtime()
    run_id = uuid4().hex[:12]

    for position, row in enumerate(dataset, start=1):
        record_id = row["ID"]
        query = row["Query"]

        if query in completed_queries:
            print(f"[{position:02d}/{len(dataset)}] {record_id} - ya guardada, se omite")
            continue

        thread_id = f"b1-{run_id}-{record_id}"
        print(f"[{position:02d}/{len(dataset)}] {record_id} - ejecutando")

        # Si falla una consulta, la excepción detiene la corrida y esa fila no
        # se escribe. Al volver a ejecutar, B1 continúa desde las ya guardadas.
        result = runtime.answer_with_langgraph(
            query,
            runtime.graph,
            thread_id=thread_id,
        )
        document, answer = validate_result(result, record_id)

        append_result(
            args.output,
            query=query,
            document=document,
            answer=answer,
        )
        completed_queries.add(query)
        print(f"[{position:02d}/{len(dataset)}] {record_id} - guardada")

    print(f"Completado: {len(dataset)}/{len(dataset)}")
    print(f"TSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
