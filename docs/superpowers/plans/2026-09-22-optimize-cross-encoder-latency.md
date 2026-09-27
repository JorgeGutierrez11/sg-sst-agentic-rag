# Optimize Cross-Encoder Latency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce request latency by limiting the CPU CrossEncoder to an initial 16-candidate post-RRF pool while preserving the current retrieval sources, model, final result count, graph behavior, and answer-quality gate.

**Architecture:** Keep the existing Chroma + BM25 source retrieval at 40 candidates per source and RRF coefficient at 60, but give the fused-output limit and CrossEncoder pool separate, explicit names and set both to 16. Keep `BAAI/bge-reranker-v2-m3` on CPU with a final reranker output of 8, and add one structured rerank telemetry event per graph invocation so the API-level A/B run can compare latency and cardinality without changing graph topology or API schemas.

**Tech Stack:** Python 3, LangGraph 1.0.4, Sentence Transformers 5.6.0 `CrossEncoder`, FastAPI, Uvicorn, ChromaDB, BM25S, standard-library `logging`, `time.perf_counter`, `math.ceil`, `unittest`, and `curl` for manual API verification.

## Global Constraints

- Preserve `RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"`, CPU execution, `RERANKER_MAX_LENGTH = 512`, and `RERANKER_FINAL_TOP_K = 8`.
- Preserve the dense and sparse source fetch at 40 candidates each; only the RRF output and CrossEncoder input pool become 16.
- Preserve `HYBRID_RRF_K = 60`, graph topology, parent expansion, retrieval relevance grading, evidence routing, prompts, generation, and API response schemas.
- Do not introduce asyncio, GPU execution, another model, grader batching, index changes, or an observability platform.
- Do not add automated tests. Update existing test doubles/assertions only where changed production interfaces require it; automated verification is regression sanity checking, not acceptance.
- The acceptance protocol is manual API A/B testing. Do not use pytest.
- Do not write evaluation outputs under tracked `data/` or `evaluation/`; use `/tmp` for logs, responses, and the review worksheet.
- Do not add or modify diagrams, dependencies, configuration files outside the runtime Python module, or technical-decision documentation.
- Do not commit as part of this plan.

---

## Current-State Finding and Intended Cardinality

The observed request took 73.2 seconds, of which CrossEncoder scoring consumed approximately 59.8 seconds (81.7%). The current runtime creates a hybrid retriever that fetches 40 Chroma candidates and 40 BM25 candidates, then passes `RERANKER_CANDIDATE_POOL_SIZE` as the third positional argument to `build_langgraph_rag`. Because that parameter is graph `top_k`, `RERANKER_CANDIDATE_POOL_SIZE = 40` also controls the RRF output. `rerank_node` consequently scores as many as 40 query-document pairs on CPU before retaining 8.

The implementation must produce this explicit flow:

```text
Chroma source fetch: 40 ─┐
                         ├─ RRF(k=60) ─ fused output: 16 ─ CrossEncoder pool: 16 ─ final: 8
BM25 source fetch:   40 ─┘
```

## File Map

| File | Action | Responsibility |
|---|---|---|
| `agents/consulta_normativa/langchain_rag/config.py` | Modify | Define unambiguous source-fetch, RRF-output, reranker-pool, batch, device, maximum-length, and final-output constants. |
| `agents/consulta_normativa/langchain_rag/main.py` | Modify | Wire the constants into hybrid retrieval, CrossEncoder creation, and graph construction exclusively with named arguments. |
| `agents/consulta_normativa/langchain_rag/graph.py` | Modify | Carry explicit reranker execution metadata into the existing `rerank` node without changing nodes or edges. |
| `agents/consulta_normativa/langchain_rag/retrieval/reranking.py` | Modify | Pin the CrossEncoder to CPU, use the explicit prediction batch size, measure rerank duration, and emit the required structured telemetry. |
| `agents/consulta_normativa/tests/test_langchain_rag_main.py` | Modify | Update existing runtime-wiring doubles and assertions for renamed constants and named arguments; add no test method. |
| `agents/consulta_normativa/tests/test_langchain_rag_reranking.py` | Modify | Update existing CrossEncoder and predictor fakes for the new production keyword arguments; add no test method. |

No other file is part of the implementation.

---

### Task 1: Separate Source Fetch, RRF Output, and Reranker Pool Configuration

**Files:**
- Modify: `agents/consulta_normativa/langchain_rag/config.py:30-40`
- Modify: `agents/consulta_normativa/langchain_rag/main.py:16,153-163,194-204`
- Modify: `agents/consulta_normativa/tests/test_langchain_rag_main.py:150-218`

**Interfaces:**
- Consumes: keyword-only `candidate_top_k: int` and `rrf_k: int` in `hybrid_retriever`, plus `top_k: int` in `build_langgraph_rag`.
- Produces: `HYBRID_SOURCE_CANDIDATE_TOP_K: int = 40`, `HYBRID_RRF_OUTPUT_TOP_K: int = 16`, `RERANKER_CANDIDATE_POOL_SIZE: int = 16`, `RERANKER_BATCH_SIZE: int = 32`, and `RERANKER_DEVICE: str = "cpu"`.
- Preserves: `HYBRID_RRF_K = 60`, `RERANKER_MAX_LENGTH = 512`, and `RERANKER_FINAL_TOP_K = 8`.

- [ ] **Step 1: Replace the ambiguous hybrid constant with separate source and output limits**

In `config.py`, replace the current hybrid/reranking block with these exact values and dependency relationships:

```python
# Hybrid Retrieval.
HYBRID_SOURCE_CANDIDATE_TOP_K = 40
HYBRID_RRF_OUTPUT_TOP_K = 16
HYBRID_RRF_K = RRF_K

# Reranking with Cross-Encoder.
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
RERANKER_DEVICE = "cpu"
RERANKER_MAX_LENGTH = 512
RERANKER_BATCH_SIZE = 32
RERANKER_CANDIDATE_POOL_SIZE = HYBRID_RRF_OUTPUT_TOP_K
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K
```

Delete `HYBRID_CANDIDATE_TOP_K`. Keep `RETRIEVAL_TOP_K`, `DEFAULT_TOP_K`, and `RRF_K` unchanged. The equality assignment makes it impossible to increase the reranker pool beyond the fused output accidentally, while retaining distinct names for the two stages.

- [ ] **Step 2: Update imports and hybrid source retrieval wiring**

In `main.py`, import the new constants using the repository's existing absolute import style. Change only the cardinality argument to the hybrid retriever:

```python
retriever = dependencies.hybrid_retriever(
    collection,
    bm25_index,
    candidate_top_k=HYBRID_SOURCE_CANDIDATE_TOP_K,
    rrf_k=HYBRID_RRF_K,
)
```

Expected behavior: Chroma and BM25 still fetch up to 40 records independently. `hybrid_retriever.retrieve(query, top_k)` continues to apply `fused_documents[:top_k]`; no change belongs in `hybrid_retrieval.py`.

- [ ] **Step 3: Remove the positional graph construction call**

Replace the graph construction in `build_runtime` with a fully named call:

```python
graph = dependencies.build_langgraph_rag(
    llm=llm,
    retriever=retriever,
    top_k=HYBRID_RRF_OUTPUT_TOP_K,
    checkpointer=checkpointer,
    store=memory_store,
    reranker=reranker,
    reranker_candidate_pool_size=RERANKER_CANDIDATE_POOL_SIZE,
    reranker_final_top_k=RERANKER_FINAL_TOP_K,
    reranker_batch_size=RERANKER_BATCH_SIZE,
    reranker_device=RERANKER_DEVICE,
    reranker_input_max_length=RERANKER_MAX_LENGTH,
    parent_lookup=parent_lookup,
)
```

This is the central correctness fix: graph `top_k` is now supplied by `HYBRID_RRF_OUTPUT_TOP_K`, never by `RERANKER_CANDIDATE_POOL_SIZE`, and all graph-construction arguments are named.

- [ ] **Step 4: Align the existing runtime-wiring test without adding a test**

In `test_langchain_rag_main.py`, keep the existing method `test_build_runtime_opens_dense_and_sparse_indexes_and_uses_hybrid_retriever_boundary`. Update its fake builder to accept keyword-only runtime wiring and record the three telemetry parameters:

```python
def fake_build_langgraph_rag(
    *,
    llm: object,
    retriever: object,
    top_k: int,
    **kwargs: object,
) -> FakeDrawableGraph:
    calls.append(
        "graph:"
        f"{llm}:{retriever}:{top_k}:"
        f"{kwargs['reranker']}:{kwargs['reranker_candidate_pool_size']}:"
        f"{kwargs['reranker_final_top_k']}:{kwargs['reranker_batch_size']}:"
        f"{kwargs['reranker_device']}:{kwargs['reranker_input_max_length']}:"
        f"{kwargs['parent_lookup']}"
    )
    return graph
```

Update the existing expected call list to use `cli.HYBRID_SOURCE_CANDIDATE_TOP_K` for the retriever, `cli.HYBRID_RRF_OUTPUT_TOP_K` for graph `top_k`, and the exact reranker values `16`, `8`, `32`, `cpu`, and `512`. Do not add another test case.

- [ ] **Step 5: Run the focused configuration regression sanity check**

Run:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main
```

Expected: all existing tests pass, and the wiring assertion proves source fetch `40`, graph/RRF output `16`, CrossEncoder pool `16`, and final output `8` are not conflated.

---

### Task 2: Add Narrow CrossEncoder Timing and Cardinality Telemetry

**Files:**
- Modify: `agents/consulta_normativa/langchain_rag/retrieval/reranking.py:1-89,127-151`
- Modify: `agents/consulta_normativa/langchain_rag/graph.py:32-69`
- Modify: `agents/consulta_normativa/langchain_rag/main.py:160-163`
- Modify: `agents/consulta_normativa/tests/test_langchain_rag_main.py:173-218`
- Modify: `agents/consulta_normativa/tests/test_langchain_rag_reranking.py:177-215`

**Interfaces:**
- Changes `get_reranker(model_name: str, max_length: int)` to `get_reranker(model_name: str, max_length: int, device: str) -> Any`.
- Extends `build_langgraph_rag` with keyword defaults `reranker_batch_size: int = 32`, `reranker_device: str = "cpu"`, and `reranker_input_max_length: int = 512`.
- Extends `rerank_node` with the same three keyword-only values.
- Extends `rerank_documents(query: str, documents: list[RetrievedDocument], reranker: Any, final_top_k: int)` with keyword-only `batch_size: int = 32`.
- Preserves the `RagGraphState` key `reranking_trace` and adds `duration_ms`, `batch_count`, `device`, and `input_max_length` to that existing dictionary.

- [ ] **Step 1: Pin the existing CrossEncoder model to the required CPU device**

Change `get_reranker` to:

```python
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
```

In `main.py`, construct it with named arguments:

```python
reranker = dependencies.get_reranker(
    model_name=RERANKER_MODEL_NAME,
    max_length=RERANKER_MAX_LENGTH,
    device=RERANKER_DEVICE,
)
```

This preserves CPU execution even on a host where Sentence Transformers would otherwise auto-select a stronger device.

- [ ] **Step 2: Carry execution metadata through graph construction without changing topology**

Add the three keyword parameters immediately after `reranker_final_top_k` in `build_langgraph_rag`:

```python
reranker_batch_size: int = 32,
reranker_device: str = "cpu",
reranker_input_max_length: int = 512,
```

Pass them only into the existing `rerank_node` call:

```python
workflow.add_node(
    "rerank",
    rerank_node(
        reranker,
        reranker_candidate_pool_size,
        reranker_final_top_k,
        batch_size=reranker_batch_size,
        device=reranker_device,
        input_max_length=reranker_input_max_length,
    ),
)
```

Do not add, remove, rename, or reorder any node or edge. In particular, preserve `normalize_documents -> rerank -> expand_parent_documents -> record_retrieval_trace -> retrieval_relevance_grading` and the existing evidence branch.

- [ ] **Step 3: Make prediction batch size explicit**

Add keyword-only `batch_size: int = 32` to `rerank_documents` and change its scoring call to:

```python
scores = reranker.predict(
    candidate_pairs,
    batch_size=batch_size,
    show_progress_bar=False,
)
```

Sentence Transformers 5.6.0 currently defaults `CrossEncoder.predict` to a batch size of 32. Passing the same value explicitly preserves execution semantics, makes `batch_count` deterministic, and removes the progress bar from production logs. It does not batch the LLM relevance grader.

- [ ] **Step 4: Measure one rerank interval per request and enrich the existing trace**

Add standard-library imports and a module logger:

```python
import logging
from math import ceil
from time import perf_counter

logger = logging.getLogger(__name__)
```

Extend `rerank_node` with keyword-only `batch_size`, `device`, and `input_max_length`. Start `perf_counter()` at the first line of `run`, after which all success, empty-input, and fallback paths must calculate:

```python
candidate_count = len(candidate_documents)
selected_count = len(selected_documents)
batch_count = ceil(candidate_count / batch_size) if candidate_count else 0
duration_ms = round((perf_counter() - started_at) * 1000, 2)
```

Add these exact keys to `reranking_trace` on every path:

```python
{
    "fallback": False,
    "candidate_count": candidate_count,
    "selected_count": selected_count,
    "duration_ms": duration_ms,
    "batch_count": batch_count,
    "device": device,
    "input_max_length": input_max_length,
}
```

The fallback path retains `"error": type(error).__name__` and sets `"fallback": True`. Pass `batch_size` from `rerank_node` into `rerank_documents`.

- [ ] **Step 5: Emit exactly one compact rerank event on every path**

After constructing each trace, log success/empty at `INFO` and fallback at `WARNING` with this exact field order:

```python
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
```

Use event text `CrossEncoder rerank fallback` and final value `True` for the exception path. Do not log the query, candidate text, generated answer, prompt, context, company identifier, exception message, or API payload. The API route's existing `duration_ms` remains the end-to-end request timer; the new event is the request-level rerank interval needed to compare the two.

- [ ] **Step 6: Update existing test doubles only**

In `test_langchain_rag_main.py`, change the existing fake `get_reranker` callable to accept named `model_name`, `max_length`, and `device`, then include `device` in its recorded call. Update only that method's expected list.

In `test_langchain_rag_reranking.py`, keep every current test method and assertion. Change `FakeCrossEncoder.__init__` and its recorded tuple to accept `device`, invoke `get_reranker("fake-model", 128, "cpu")`, and change `FakeReranker.predict` plus `FailingReranker.predict` to accept these keyword-only arguments:

```python
def predict(
    self,
    pairs: list[tuple[str, str]],
    *,
    batch_size: int,
    show_progress_bar: bool,
) -> list[float]:
```

The fake should continue recording `pairs` and returning the configured scores; the failing fake should continue raising `RuntimeError`. Do not create a telemetry-specific unit test because this first production optimization is accepted through the manual API protocol below.

- [ ] **Step 7: Run focused reranking regression sanity checks**

Run:

```bash
python -m unittest \
  agents.consulta_normativa.tests.test_langchain_rag_reranking \
  agents.consulta_normativa.tests.test_langchain_rag_graph \
  agents.consulta_normativa.tests.test_langchain_rag_main
```

Expected: all existing tests pass. This is a regression check only; it does not accept the latency change.

---

### Task 3: Run Repository Regression Sanity Checks

**Files:**
- No file changes.

**Interfaces:**
- Consumes: the repository's documented `unittest` and compile commands.
- Produces: evidence that the narrow runtime change did not break existing consultation behavior or Python syntax.

- [ ] **Step 1: Run the consultation-agent suite**

Run from the repository root:

```bash
python -m unittest discover -s agents/consulta_normativa/tests
```

Expected: the existing suite passes. Resolve failures caused by the changed signatures only within the six files listed in the File Map; do not broaden implementation scope.

- [ ] **Step 2: Compile the affected package**

Run:

```bash
python -m compileall agents/consulta_normativa
```

Expected: successful compilation with no syntax errors.

---

### Task 4: MANUAL TEST — Establish the Instrumented 40-Candidate Baseline

**Files:**
- Temporarily modify during measurement: `agents/consulta_normativa/langchain_rag/config.py`
- Store untracked measurement artifacts only under: `/tmp/sg-sst-reranker-ab/`

**Interfaces:**
- Consumes: `POST /api/v1/query`, existing API `duration_ms`, and the new `CrossEncoder rerank completed` event.
- Produces: 40 warm baseline request records and response bodies using the post-change code with baseline cardinalities.

- [ ] **Step 1: Set only the two experimental limits to the current baseline**

Temporarily set:

```python
HYBRID_RRF_OUTPUT_TOP_K = 40
RERANKER_CANDIDATE_POOL_SIZE = HYBRID_RRF_OUTPUT_TOP_K
```

Keep `HYBRID_SOURCE_CANDIDATE_TOP_K = 40`, model, CPU, maximum length, batch size, final top-k, graph, grader, and every other value unchanged. This isolates candidate cardinality while retaining the newly instrumented code in both A and B.

- [ ] **Step 2: Prepare the temporary output location**

Run:

```bash
mkdir -p /tmp/sg-sst-reranker-ab/baseline/responses
: > /tmp/sg-sst-reranker-ab/baseline/request-times.tsv
```

- [ ] **Step 3: Start the API without development reload**

With the normal environment and dependencies prepared as documented by the repository:

```bash
read -rsp "DeepSeek API key: " DEEPSEEK_API_KEY
printf '\n'
export DEEPSEEK_API_KEY
python -m uvicorn agents.consulta_normativa.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level info \
  2>&1 | tee /tmp/sg-sst-reranker-ab/baseline/server.log
```

If `DEEPSEEK_API_KEY` is already exported, omit the `read`, `printf`, and `export` lines. Expected startup observable: the runtime opens the existing Chroma and BM25 indexes and loads `BAAI/bge-reranker-v2-m3` once on CPU. Do not include startup/model-load time in request statistics.

- [ ] **Step 4: Verify health and execute one excluded cold request**

In a second terminal, run:

```bash
curl --fail-with-body http://127.0.0.1:8000/health
curl --fail-with-body \
  -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Cómo debo conservar los documentos y registros de mi SG-SST?","conversation_id":"baseline-cold-excluded"}' \
  > /tmp/sg-sst-reranker-ab/baseline/responses/cold-excluded.json
```

Expected: health returns `{"status":"ok"}` and the query returns HTTP 200 with non-empty `answer`, `references`, `chunks`, and the supplied `conversation_id`. Mark this first request as cold and exclude both its API and rerank durations from comparison.

- [ ] **Step 5: Run five warm repetitions of the fixed eight-question set**

The set is a fixed Conjunto B1 subset covering all eight normative sources in the legal corpus:

```text
B003 — Mi actividad económica no aparece en la tabla de clasificación de riesgos. ¿Qué debo hacer en ese caso?
B010 — ¿Cómo debo conservar los documentos y registros de mi SG-SST?
B021 — Mi empresa es de riesgo I y creció de 8 a 15 trabajadores. ¿Qué estándares mínimos debo cumplir ahora?
B043 — Mi empresa está terminando el informe de investigación de un accidente de trabajo. ¿Qué información debe contener ese informe?
B053 — Denuncié un caso de acoso laboral y temo represalias de mi jefe. ¿Qué garantías tengo después de presentar la denuncia?
B060 — Mi empresa va a contratar a una persona mediante un contrato de prestación de servicios. ¿También debemos cotizar riesgos laborales por ese contratista independiente?
B069 — En una reunión del Comité Paritario solo está presente la mitad de sus miembros. ¿Con cuántos miembros puede sesionar válidamente?
B075 — ¿Qué tipos de evaluaciones médicas ocupacionales debe realizar mi empresa?
```

Run sequentially, never concurrently:

```bash
CONFIG=baseline
CASES=(
  'B003|Mi actividad económica no aparece en la tabla de clasificación de riesgos. ¿Qué debo hacer en ese caso?'
  'B010|¿Cómo debo conservar los documentos y registros de mi SG-SST?'
  'B021|Mi empresa es de riesgo I y creció de 8 a 15 trabajadores. ¿Qué estándares mínimos debo cumplir ahora?'
  'B043|Mi empresa está terminando el informe de investigación de un accidente de trabajo. ¿Qué información debe contener ese informe?'
  'B053|Denuncié un caso de acoso laboral y temo represalias de mi jefe. ¿Qué garantías tengo después de presentar la denuncia?'
  'B060|Mi empresa va a contratar a una persona mediante un contrato de prestación de servicios. ¿También debemos cotizar riesgos laborales por ese contratista independiente?'
  'B069|En una reunión del Comité Paritario solo está presente la mitad de sus miembros. ¿Con cuántos miembros puede sesionar válidamente?'
  'B075|¿Qué tipos de evaluaciones médicas ocupacionales debe realizar mi empresa?'
)

for run in 1 2 3 4 5; do
  for item in "${CASES[@]}"; do
    IFS='|' read -r case_id question <<< "$item"
    conversation_id="${CONFIG}-r${run}-${case_id}"
    payload=$(python -c 'import json, sys; print(json.dumps({"question": sys.argv[1], "conversation_id": sys.argv[2]}, ensure_ascii=False))' "$question" "$conversation_id")
    curl --fail-with-body --silent --show-error \
      -X POST http://127.0.0.1:8000/api/v1/query \
      -H "Content-Type: application/json" \
      -d "$payload" \
      -o "/tmp/sg-sst-reranker-ab/${CONFIG}/responses/r${run}-${case_id}.json" \
      -w "${CONFIG}\t${run}\t${case_id}\t%{http_code}\t%{time_total}\n" \
      >> "/tmp/sg-sst-reranker-ab/${CONFIG}/request-times.tsv" || exit 1
  done
done
```

Expected baseline observables for each of the 40 measured requests:

- HTTP status is 200.
- One API completion event and one CrossEncoder rerank event are logged.
- `candidate_count` is at most 40, `selected_count` is at most 8, `batch_count` equals `ceil(candidate_count / 32)`, `device=cpu`, `input_max_length=512`, and `fallback=False`.
- A count below 40 is valid after dense/sparse deduplication; it is not permission to fetch fewer than 40 from either source.

- [ ] **Step 6: Stop the baseline server cleanly**

Press `Ctrl-C` in the Uvicorn terminal after the final request. Preserve `/tmp/sg-sst-reranker-ab/baseline/` for comparison.

---

### Task 5: MANUAL TEST — Run the 16-Candidate Candidate Configuration

**Files:**
- Restore final values in: `agents/consulta_normativa/langchain_rag/config.py`
- Store untracked measurement artifacts only under: `/tmp/sg-sst-reranker-ab/candidate/`

**Interfaces:**
- Consumes: the same API endpoint, questions, order, run count, host, and hardware as the baseline.
- Produces: 40 warm candidate request records and response bodies.

- [ ] **Step 1: Restore the intended production values before starting the server**

Set and leave the working tree with:

```python
HYBRID_SOURCE_CANDIDATE_TOP_K = 40
HYBRID_RRF_OUTPUT_TOP_K = 16
RERANKER_CANDIDATE_POOL_SIZE = HYBRID_RRF_OUTPUT_TOP_K
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K
```

Confirm `DEFAULT_TOP_K` remains 8. This is the final configuration if the acceptance gate passes.

- [ ] **Step 2: Prepare candidate outputs and start a fresh process**

Run:

```bash
mkdir -p /tmp/sg-sst-reranker-ab/candidate/responses
: > /tmp/sg-sst-reranker-ab/candidate/request-times.tsv
python -m uvicorn agents.consulta_normativa.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level info \
  2>&1 | tee /tmp/sg-sst-reranker-ab/candidate/server.log
```

- [ ] **Step 3: Execute and exclude the candidate cold request**

In the second terminal, run the same health call and question with a distinct conversation ID:

```bash
curl --fail-with-body http://127.0.0.1:8000/health
curl --fail-with-body \
  -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Cómo debo conservar los documentos y registros de mi SG-SST?","conversation_id":"candidate-cold-excluded"}' \
  > /tmp/sg-sst-reranker-ab/candidate/responses/cold-excluded.json
```

Exclude this request exactly as in the baseline.

- [ ] **Step 4: Repeat the exact warm-run command with only the configuration label changed**

Reuse the `CASES` array from Task 4 and run:

```bash
CONFIG=candidate
for run in 1 2 3 4 5; do
  for item in "${CASES[@]}"; do
    IFS='|' read -r case_id question <<< "$item"
    conversation_id="${CONFIG}-r${run}-${case_id}"
    payload=$(python -c 'import json, sys; print(json.dumps({"question": sys.argv[1], "conversation_id": sys.argv[2]}, ensure_ascii=False))' "$question" "$conversation_id")
    curl --fail-with-body --silent --show-error \
      -X POST http://127.0.0.1:8000/api/v1/query \
      -H "Content-Type: application/json" \
      -d "$payload" \
      -o "/tmp/sg-sst-reranker-ab/${CONFIG}/responses/r${run}-${case_id}.json" \
      -w "${CONFIG}\t${run}\t${case_id}\t%{http_code}\t%{time_total}\n" \
      >> "/tmp/sg-sst-reranker-ab/${CONFIG}/request-times.tsv" || exit 1
  done
done
```

Expected candidate observables: `candidate_count <= 16`, `selected_count <= 8`, `batch_count` is 1 for non-empty input, `device=cpu`, `input_max_length=512`, and `fallback=False` for every measured request. Stop Uvicorn cleanly after the run.

---

### Task 6: MANUAL TEST — Calculate Latency and Perform the ARES-Aligned Quality Gate

**Files:**
- No repository file changes.
- Read: `/tmp/sg-sst-reranker-ab/{baseline,candidate}/server.log`
- Read: `/tmp/sg-sst-reranker-ab/{baseline,candidate}/request-times.tsv`
- Read: `/tmp/sg-sst-reranker-ab/{baseline,candidate}/responses/*.json`
- Create outside the repository: `/tmp/sg-sst-reranker-ab/quality-review.tsv`

**Interfaces:**
- Consumes: 40 warm observations per configuration and API response `answer`, `references`, and `chunks`.
- Produces: p50/p95 rerank and end-to-end duration, plus a manual quality no-regression decision.

- [ ] **Step 1: Calculate p50 and p95 from each server log and client timing file**

Run this exact parser for both labels:

```bash
for config in baseline candidate; do
  python - "$config" <<'PY'
import re
import statistics
import sys
from pathlib import Path

config = sys.argv[1]
root = Path("/tmp/sg-sst-reranker-ab") / config
log_text = (root / "server.log").read_text(encoding="utf-8")
rerank_values = [
    float(value)
    for value in re.findall(
        r"CrossEncoder rerank completed \| duration_ms=([0-9.]+)",
        log_text,
    )
][1:]
request_values = []
for line in (root / "request-times.tsv").read_text(encoding="utf-8").splitlines():
    fields = line.split("\t")
    if len(fields) == 5 and fields[3] == "200":
        request_values.append(float(fields[4]) * 1000)

if len(rerank_values) != 40 or len(request_values) != 40:
    raise SystemExit(
        f"{config}: expected 40 warm rerank and request values, "
        f"got {len(rerank_values)} and {len(request_values)}"
    )

def percentile_95(values: list[float]) -> float:
    return statistics.quantiles(values, n=100, method="inclusive")[94]

print(f"{config} rerank_count={len(rerank_values)}")
print(f"{config} rerank_p50_ms={statistics.median(rerank_values):.2f}")
print(f"{config} rerank_p95_ms={percentile_95(rerank_values):.2f}")
print(f"{config} request_p50_ms={statistics.median(request_values):.2f}")
print(f"{config} request_p95_ms={percentile_95(request_values):.2f}")
PY
```

The `[1:]` removes exactly the excluded cold request from the server events. The client timing files contain only warm requests and therefore need no removal.

- [ ] **Step 2: Apply the manual ARES-aligned quality rubric**

The repository methodology assigns Conjunto B to development optimization and defines three ARES dimensions: Context Relevance, Answer Faithfulness, and Answer Relevance. However, `evaluation/ares/` currently contains only `.gitkeep`, Conjunto A calibration data is not present, and the existing Conjunto B runner only exports `Query`, `Document`, and `Answer`; it does not execute a calibrated ARES evaluator. Therefore, do not report these manual judgments as official ARES scores or confidence intervals.

For each of the eight case IDs and each of five runs, compare baseline and candidate responses side by side. Have the reviewer evaluate unlabeled A/B copies when practical, then record one binary value per response for each dimension in `/tmp/sg-sst-reranker-ab/quality-review.tsv`:

```text
configuration	run	case_id	context_relevance	answer_faithfulness	answer_relevance	critical_legal_regression	notes
```

Use these exact criteria:

- `context_relevance = 1` only when the returned `chunks` and `references` contain evidence directly relevant to the fixed question and the expected normative topic; otherwise `0`.
- `answer_faithfulness = 1` only when every material legal obligation, exception, deadline, threshold, sanction, and cited norm in `answer` is supported by the returned chunks; otherwise `0`.
- `answer_relevance = 1` only when the answer directly addresses the user's situation, remains within the question's scope, and gives the requested normative guidance; otherwise `0`.
- `critical_legal_regression = 1` when the 16-candidate response loses a controlling norm, states an unsupported duty/prohibition, changes a worker-count or risk-class threshold, invents a deadline/sanction, or becomes unable to answer where the paired baseline answered with support.

For each case and dimension, calculate the pass rate as passed runs divided by five. The candidate must be greater than or equal to the baseline on all 24 case-dimension comparisons, and no candidate row may have `critical_legal_regression = 1`.

- [ ] **Step 3: Apply the complete acceptance gate**

Accept the 16-candidate configuration only if all conditions pass:

1. All 80 measured requests return HTTP 200: 40 baseline and 40 candidate.
2. Every candidate event has `candidate_count <= 16`, `selected_count <= 8`, `batch_count = 1` when candidates are non-empty, `device=cpu`, `input_max_length=512`, and `fallback=False`.
3. Candidate rerank p50 is at most 60% of measured baseline rerank p50 (at least 40% reduction).
4. Candidate rerank p95 is at most 70% of measured baseline rerank p95 (at least 30% reduction).
5. Candidate end-to-end request p50 is at most 75% of measured baseline request p50 (at least 25% reduction).
6. Candidate end-to-end request p95 does not exceed measured baseline request p95.
7. All 24 per-case quality pass rates are greater than or equal to baseline and no critical legal regression is recorded.
8. Final source code has `HYBRID_SOURCE_CANDIDATE_TOP_K = 40`, `HYBRID_RRF_OUTPUT_TOP_K = 16`, `RERANKER_CANDIDATE_POOL_SIZE = HYBRID_RRF_OUTPUT_TOP_K`, and final top-k 8.

The historical 59.8-second rerank and 73.2-second request explain the optimization, but acceptance uses the instrumented same-host A/B measurements, not those single historical samples.

- [ ] **Step 4: Apply the exact rollback condition if any gate fails**

If any acceptance condition fails, restore only the optimized cardinalities:

```python
HYBRID_SOURCE_CANDIDATE_TOP_K = 40
HYBRID_RRF_OUTPUT_TOP_K = 40
RERANKER_CANDIDATE_POOL_SIZE = HYBRID_RRF_OUTPUT_TOP_K
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K
```

Keep the named graph call, CPU pinning, explicit batch size, and telemetry because they fix ambiguity and make the baseline measurable. Restart the API and manually repeat the health check plus B003 once; confirm HTTP 200, `candidate_count <= 40`, `selected_count <= 8`, `device=cpu`, `input_max_length=512`, and `fallback=False`. Do not attempt a second optimization, model change, GPU move, async conversion, or grader batching in this implementation.

---

## Risks and Controls

| Risk | Control |
|---|---|
| Relevant evidence ranks between fused positions 17 and 40 and is no longer reranked. | Keep both source fetches at 40, use the eight-topic Conjunto B subset, compare all three ARES-aligned dimensions, and roll back on any measured quality regression. |
| External DeepSeek latency obscures the CPU improvement. | Measure rerank and end-to-end intervals separately, use the same machine and fixed question order, exclude one cold request, and collect 40 warm observations per configuration. |
| Conversation memory contaminates repeated runs. | Supply a unique `conversation_id` for every request and run requests sequentially. |
| RRF deduplication yields fewer candidates than configured. | Treat cardinalities as upper bounds and verify `batch_count = ceil(candidate_count / 32)` rather than requiring exactly 40 or 16. |
| Device auto-selection changes the comparison. | Pass `device="cpu"` explicitly to `CrossEncoder` and log `device=cpu` on every invocation. |
| Logging leaks normative queries or company information. | Log only duration, counts, batch count, device, maximum input length, and fallback status; never log request or document content. |
| Telemetry changes failure behavior. | Preserve the current conservative fallback and include the same telemetry fields on fallback without exposing exception messages. |
| Existing tests encode the old positional wiring. | Update only existing doubles/assertions needed by the production signature; add no automated test and use manual API acceptance. |
| Formal ARES capability is mistaken for available tooling. | Label the quality gate ARES-aligned and manual; do not claim calibrated ARES metrics until Conjunto A calibration and evaluator tooling exist. |

## Final Verification Checklist

- [ ] `python -m unittest discover -s agents/consulta_normativa/tests` passes.
- [ ] `python -m compileall agents/consulta_normativa` passes.
- [ ] Baseline and candidate each contain exactly 40 warm API responses plus one excluded cold response.
- [ ] p50/p95 rerank and end-to-end request durations are documented from same-host runs.
- [ ] Every candidate event reports the required telemetry fields and no fallback.
- [ ] Manual quality review covers 8 fixed questions × 5 runs × 3 ARES-aligned dimensions.
- [ ] The final working tree contains the accepted 16/16/8 configuration, or the exact 40/40/8 rollback configuration if any gate failed.
- [ ] No application file outside the six-file File Map changed.
- [ ] No tracked data, evaluation output, diagram, dependency manifest, or unrelated file changed.

## Self-Review

- **Coverage:** Pass. The plan separates source fetch (40), RRF output (16), CrossEncoder pool (16), and final output (8); removes positional graph wiring; preserves model/CPU/graph/grading behavior; specifies all required telemetry; and includes a fixed, repeatable manual A/B quality and latency gate.
- **Placeholder scan:** Pass. All production symbols, values, files, commands, questions, fields, thresholds, expected observables, and rollback values are explicit. The API key is intentionally supplied through the environment and is never persisted.
- **Type/config consistency:** Pass. `int` limits flow from `config.py` through named `main.py` arguments into `build_langgraph_rag`, then `rerank_node` and `rerank_documents`; `device` remains `str`; `RERANKER_CANDIDATE_POOL_SIZE` derives from `HYBRID_RRF_OUTPUT_TOP_K`; and `RERANKER_FINAL_TOP_K` derives from the unchanged `DEFAULT_TOP_K = 8`.
- **Scope consistency:** Pass. No asyncio, GPU, model replacement, grader batching, topology change, API schema change, index rebuild, broad observability work, new automated test, pytest command, or commit command is included.
