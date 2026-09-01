# Normative RAG API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the current SG-SST LangGraph RAG through a minimal FastAPI backend so a web system can query it over HTTP without duplicating RAG logic.

**Architecture:** Add a thin API layer under `agents/consulta_normativa/api/` that reuses the existing LangGraph runtime. Load DeepSeek, Chroma, BM25, parent lookup, and the compiled graph once during FastAPI lifespan. This first version does not add durable chat history: `conversation_id` is correlation/session metadata only.

**Tech Stack:** Python, FastAPI, Pydantic, Uvicorn, FastAPI `TestClient`, existing LangGraph RAG runtime, `unittest`.

## Global Constraints

- Do not modify `pipeline/`; it remains offline corpus transformation/indexing only.
- Do not move this first API into `app/backend/`; that directory is still placeholder scaffolding.
- Do not duplicate retrieval, BM25, Chroma, parent expansion, prompting, validation, or DeepSeek logic inside the API.
- Do not add frontend, authentication, PostgreSQL, WebSockets, SSE streaming, or durable chat persistence in this stage.
- `conversation_id` is not memory. It is only returned to the client and used for request/session correlation until a future LangGraph checkpointer exists.
- Do not log API keys, authorization headers, full prompts, full answers, full contexts, raw company data, or confidential identifiers.
- Use `python -m unittest`, not pytest.
- Keep implementation KISS/YAGNI: small files, explicit dependencies, no generic framework abstractions.

---

## Current architecture to preserve

The LangGraph runtime is already mostly separated from terminal I/O:

- `agents/consulta_normativa/langchain_rag/main.py`
  - `build_runtime()` builds the reusable runtime once.
  - `RagRuntime` stores `answer_with_langgraph` and the compiled `graph`.
  - `run_once()` is only a CLI adapter around the runtime.
- `agents/consulta_normativa/langchain_rag/graph.py`
  - `answer_with_langgraph(question, graph)` calls `graph.invoke({"question": question})` and returns `LangChainRagResult`.
- `agents/consulta_normativa/langchain_rag/models.py`
  - `LangChainRagResult` exposes `answer`, `references`, `context`, and `prompt`.

The API should wrap this existing runtime instead of refactoring the RAG engine from scratch.

## Target API

### `GET /health`

Response:

```json
{
  "status": "ok"
}
```

The app should fail during startup if the RAG runtime cannot be built. `GET /health` should not call DeepSeek or execute a real RAG query.

### `POST /api/v1/query`

Request:

```json
{
  "question": "¿Qué estándares mínimos debe cumplir una empresa de 8 trabajadores riesgo I?",
  "conversation_id": "abc-123"
}
```

Response:

```json
{
  "answer": "...",
  "references": ["Resolución 0312 de 2019 ..."],
  "conversation_id": "abc-123"
}
```

If `conversation_id` is omitted, the API generates one UUID string and returns it. In this stage, the generated ID does **not** enable multi-turn memory.

---

## File structure

Create:

```text
agents/consulta_normativa/api/
├── __init__.py
├── main.py
├── schemas.py
├── routes.py
├── dependencies.py
├── service.py
└── errors.py
```

Modify:

```text
requirements.txt
agents/consulta_normativa/langchain_rag/main.py
agents/consulta_normativa/tests/test_api.py
```

Responsibilities:

| File | Responsibility |
|---|---|
| `api/main.py` | Create the FastAPI app, configure lifespan, include routers. |
| `api/schemas.py` | Define request/response/error schemas. |
| `api/routes.py` | Define thin HTTP endpoints. |
| `api/dependencies.py` | Retrieve shared app resources from FastAPI state. |
| `api/service.py` | Adapt API request data to the existing `RagRuntime`. |
| `api/errors.py` | Define API-safe application exceptions and HTTP error mapping. |
| `tests/test_api.py` | Test API behavior with fakes; no DeepSeek, Chroma, or BM25 calls. |

---

## Task 1: Add API dependencies

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces import availability for FastAPI, Uvicorn, and TestClient dependencies.

- [ ] **Step 1: Add dependencies**

Add:

```txt
fastapi
uvicorn
httpx
```

Keep existing Pydantic and LangChain dependencies unchanged.

- [ ] **Step 2: Verify imports after installing requirements**

Run:

```bash
python - <<'PY'
from fastapi import FastAPI
from fastapi.testclient import TestClient
print(FastAPI.__name__, TestClient.__name__)
PY
```

Expected: prints `FastAPI TestClient`.

---

## Task 2: Make graph image generation optional for server startup

**Files:**
- Modify: `agents/consulta_normativa/langchain_rag/main.py`
- Test: `agents/consulta_normativa/tests/test_langchain_rag_main.py`

**Why:** `build_runtime()` currently writes `data/images/base_rag_graph.png` during startup. API startup should not fail because an optional development artifact cannot be written.

**Interfaces:**
- Change `build_runtime()` signature to `build_runtime(write_graph_image: bool = True) -> RagRuntime`.
- CLI keeps existing behavior by using default `True`.
- API calls `build_runtime(write_graph_image=False)`.

- [ ] **Step 1: Write test for disabling graph image output**

In `test_langchain_rag_main.py`, add/adjust a runtime test using existing fakes:

```python
def test_build_runtime_can_skip_graph_image_output(self) -> None:
    dependencies = fake_runtime_dependencies()

    runtime = build_runtime(write_graph_image=False, dependencies=dependencies)

    self.assertIsNotNone(runtime.graph)
    self.assertFalse(dependencies.graph.draw_mermaid_png_called)
```

If `build_runtime()` does not currently accept injected dependencies in tests, follow the existing test pattern in this file and only assert the graph image function is not called when the flag is false.

- [ ] **Step 2: Implement optional flag**

Wrap graph image generation:

```python
if write_graph_image:
    png_bytes = graph.get_graph().draw_mermaid_png()
    with open("data/images/base_rag_graph.png", "wb") as f:
        f.write(png_bytes)
    print("Grafo guardado exitosamente como 'base_rag_graph.png'")
```

- [ ] **Step 3: Run tests**

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main
```

Expected: PASS.

---

## Task 3: Define API schemas

**Files:**
- Create: `agents/consulta_normativa/api/__init__.py`
- Create: `agents/consulta_normativa/api/schemas.py`
- Test: `agents/consulta_normativa/tests/test_api.py`

**Interfaces:**
- Produces `QueryRequest`.
- Produces `QueryResponse`.
- Produces `HealthResponse`.

- [ ] **Step 1: Write schema tests**

Create `agents/consulta_normativa/tests/test_api.py` with `unittest.TestCase`.

Test validation:

```python
import unittest
from pydantic import ValidationError

from agents.consulta_normativa.api.schemas import QueryRequest, QueryResponse


class ApiSchemaTests(unittest.TestCase):
    def test_query_request_rejects_blank_question(self) -> None:
        with self.assertRaises(ValidationError):
            QueryRequest(question="   ")

    def test_query_response_shape(self) -> None:
        response = QueryResponse(answer="Respuesta", references=["Referencia"], conversation_id="abc")

        self.assertEqual(response.answer, "Respuesta")
        self.assertEqual(response.references, ["Referencia"])
        self.assertEqual(response.conversation_id, "abc")
```

- [ ] **Step 2: Implement schemas**

```python
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    question: Annotated[str, Field(min_length=1)]
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value.strip()


class QueryResponse(BaseModel):
    answer: str
    references: list[str]
    conversation_id: str


class HealthResponse(BaseModel):
    status: str
```

- [ ] **Step 3: Run schema tests**

```bash
python -m unittest agents.consulta_normativa.tests.test_api
```

Expected: schema tests pass or fail only because later API modules are not created yet.

---

## Task 4: Create the query service boundary

**Files:**
- Create: `agents/consulta_normativa/api/service.py`
- Test: `agents/consulta_normativa/tests/test_api.py`

**Interfaces:**
- Consumes existing `RagRuntime` with `answer_with_langgraph(question, graph)` and `graph`.
- Produces `QueryService.ask(question: str, conversation_id: str | None = None) -> QueryResponse`.

**Decision:** `conversation_id` is correlation-only in this stage. Do not pass it as LangGraph `thread_id` because the graph has no checkpointer or memory.

- [ ] **Step 1: Write service tests**

```python
class FakeRuntime:
    def __init__(self) -> None:
        self.graph = object()
        self.questions: list[str] = []

    def answer_with_langgraph(self, question: str, graph: object) -> object:
        self.questions.append(question)
        return SimpleNamespace(answer="Respuesta", references=["Ref"], context="ctx", prompt="prompt")


class QueryServiceTests(unittest.TestCase):
    def test_ask_returns_response_with_given_conversation_id(self) -> None:
        service = QueryService(FakeRuntime())

        response = service.ask("¿Qué es el SG-SST?", conversation_id="abc")

        self.assertEqual(response.answer, "Respuesta")
        self.assertEqual(response.references, ["Ref"])
        self.assertEqual(response.conversation_id, "abc")

    def test_ask_generates_conversation_id_when_missing(self) -> None:
        service = QueryService(FakeRuntime())

        response = service.ask("¿Qué es el SG-SST?")

        self.assertTrue(response.conversation_id)
```

- [ ] **Step 2: Implement service**

```python
from uuid import uuid4
from typing import Any

from agents.consulta_normativa.api.schemas import QueryResponse


class QueryService:
    """Application boundary for asking the current LangGraph RAG runtime."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    def ask(self, question: str, conversation_id: str | None = None) -> QueryResponse:
        result = self.runtime.answer_with_langgraph(question, self.runtime.graph)
        return QueryResponse(
            answer=result.answer,
            references=list(result.references),
            conversation_id=conversation_id or str(uuid4()),
        )
```

- [ ] **Step 3: Run service tests**

```bash
python -m unittest agents.consulta_normativa.tests.test_api
```

Expected: PASS for schema/service tests.

---

## Task 5: Add dependencies and error mapping

**Files:**
- Create: `agents/consulta_normativa/api/dependencies.py`
- Create: `agents/consulta_normativa/api/errors.py`
- Test: `agents/consulta_normativa/tests/test_api.py`

**Interfaces:**
- Produces `get_query_service(request: Request) -> QueryService`.
- Produces API-safe exception types or handlers.

- [ ] **Step 1: Write dependency test for missing service**

```python
def test_get_query_service_fails_when_service_missing(self) -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    with self.assertRaises(RuntimeError):
        get_query_service(request)
```

- [ ] **Step 2: Implement dependency**

```python
from fastapi import Request

from agents.consulta_normativa.api.service import QueryService


def get_query_service(request: Request) -> QueryService:
    service = getattr(request.app.state, "query_service", None)
    if not isinstance(service, QueryService):
        raise RuntimeError("Query service is not initialized.")
    return service
```

- [ ] **Step 3: Implement minimal error type**

```python
class QueryExecutionError(Exception):
    """API-safe error raised when RAG execution fails."""
```

Only add broader custom handlers if tests require them. Keep this first pass small.

---

## Task 6: Implement API routes

**Files:**
- Create: `agents/consulta_normativa/api/routes.py`
- Test: `agents/consulta_normativa/tests/test_api.py`

**Interfaces:**
- Produces `router` with `GET /health` and `POST /api/v1/query`.

- [ ] **Step 1: Write route tests with fake service**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeQueryService:
    def ask(self, question: str, conversation_id: str | None = None) -> QueryResponse:
        return QueryResponse(answer="Respuesta fake", references=["Ref"], conversation_id=conversation_id or "generated")


class ApiRouteTests(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        app = create_test_app(FakeQueryService())
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_query_returns_answer(self) -> None:
        app = create_test_app(FakeQueryService())
        client = TestClient(app)

        response = client.post("/api/v1/query", json={"question": "¿Qué es SG-SST?", "conversation_id": "abc"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Respuesta fake")
        self.assertEqual(response.json()["references"], ["Ref"])
        self.assertEqual(response.json()["conversation_id"], "abc")

    def test_query_rejects_blank_question(self) -> None:
        app = create_test_app(FakeQueryService())
        client = TestClient(app)

        response = client.post("/api/v1/query", json={"question": "   "})

        self.assertEqual(response.status_code, 422)
```

- [ ] **Step 2: Implement routes**

```python
from fastapi import APIRouter, Depends, HTTPException

from agents.consulta_normativa.api.dependencies import get_query_service
from agents.consulta_normativa.api.schemas import HealthResponse, QueryRequest, QueryResponse
from agents.consulta_normativa.api.service import QueryService


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/api/v1/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    service: QueryService = Depends(get_query_service),
) -> QueryResponse:
    try:
        return service.ask(request.question, request.conversation_id)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="The normative consultation service is temporarily unavailable.",
        ) from error
```

Do not return `context`, `prompt`, graph state, traces, or raw retrieval data in the public response.

---

## Task 7: Implement FastAPI app and lifespan

**Files:**
- Create: `agents/consulta_normativa/api/main.py`
- Test: `agents/consulta_normativa/tests/test_api.py`

**Interfaces:**
- Produces `create_app(runtime_builder: Callable[[], Any] | None = None) -> FastAPI`.
- Produces module-level `app = create_app()` for Uvicorn/FastAPI CLI.

- [ ] **Step 1: Write app lifespan test**

```python
def test_app_lifespan_builds_query_service_once(self) -> None:
    calls = []

    def runtime_builder() -> FakeRuntime:
        calls.append("built")
        return FakeRuntime()

    app = create_app(runtime_builder=runtime_builder)

    with TestClient(app) as client:
        response = client.get("/health")

    self.assertEqual(response.status_code, 200)
    self.assertEqual(calls, ["built"])
```

- [ ] **Step 2: Implement app factory**

```python
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from agents.consulta_normativa.api.routes import router
from agents.consulta_normativa.api.service import QueryService
from agents.consulta_normativa.langchain_rag.main import build_runtime


def create_app(runtime_builder: Callable[[], Any] | None = None) -> FastAPI:
    builder = runtime_builder or (lambda: build_runtime(write_graph_image=False))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = builder()
        app.state.query_service = QueryService(runtime)
        yield

    app = FastAPI(title="SG-SST Normative RAG API", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
```

- [ ] **Step 3: Run API tests**

```bash
python -m unittest agents.consulta_normativa.tests.test_api
```

Expected: PASS.

---

## Task 8: Add minimal operational logging without chat persistence

**Files:**
- Modify: `agents/consulta_normativa/api/routes.py`
- Test: `agents/consulta_normativa/tests/test_api.py`

**Decision:** This project currently does not persist chats or interaction history. This task adds only operational logs for observability. It does not store conversations in files or a database.

**Allowed log fields:**

- `request_id`
- `conversation_id`
- endpoint path
- status code
- duration in milliseconds
- error type for failures

**Forbidden log fields:**

- API keys
- auth headers
- full question
- full answer
- full prompt
- full context
- retrieved documents
- company/person identifiers

- [ ] **Step 1: Add request ID generation inside query route**

Use `uuid4()` and `time.perf_counter()`.

- [ ] **Step 2: Log success and failure**

Example implementation pattern:

```python
import logging
from time import perf_counter
from uuid import uuid4

logger = logging.getLogger(__name__)


@router.post("/api/v1/query", response_model=QueryResponse)
def query(...):
    request_id = str(uuid4())
    started_at = perf_counter()
    try:
        response = service.ask(request.question, request.conversation_id)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "API query completed | request_id=%s | conversation_id=%s | status_code=200 | duration_ms=%s",
            request_id,
            response.conversation_id,
            duration_ms,
        )
        return response
    except Exception as error:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.error(
            "API query failed | request_id=%s | conversation_id=%s | status_code=503 | duration_ms=%s | error=%s",
            request_id,
            request.conversation_id,
            duration_ms,
            type(error).__name__,
        )
        raise HTTPException(status_code=503, detail="The normative consultation service is temporarily unavailable.") from error
```

- [ ] **Step 3: Test that failures return sanitized error**

Use a fake service that raises `RuntimeError("secret details")` and assert:

```python
self.assertEqual(response.status_code, 503)
self.assertEqual(response.json(), {"detail": "The normative consultation service is temporarily unavailable."})
self.assertNotIn("secret details", response.text)
```

---

## Task 9: Preserve CLI behavior

**Files:**
- Test: `agents/consulta_normativa/tests/test_langchain_rag_main.py`

- [ ] **Step 1: Run existing CLI/runtime tests**

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_cli
```

Expected: existing CLI tests continue passing.

- [ ] **Step 2: Manual CLI smoke test**

With the normal environment configured:

```bash
python -m agents.consulta_normativa.langchain_rag.main "¿Qué es el SG-SST?"
```

Expected: same terminal behavior as before.

---

## Task 10: Local API smoke test

**Files:**
- No code changes.

- [ ] **Step 1: Start API**

Use one of:

```bash
python -m uvicorn agents.consulta_normativa.api.main:app --reload
```

or:

```bash
fastapi dev agents/consulta_normativa/api/main.py
```

- [ ] **Step 2: Check health**

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

- [ ] **Step 3: Query the RAG**

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Qué es el SG-SST?"}'
```

Expected:

```json
{
  "answer": "...",
  "references": [...],
  "conversation_id": "..."
}
```

Do not assert an exact answer string in the smoke test.

---

## Final verification

Run:

```bash
python -m unittest agents.consulta_normativa.tests.test_api
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_cli
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph
python -m compileall agents/consulta_normativa/api agents/consulta_normativa/langchain_rag agents/shared
```

## Acceptance criteria

- API starts with RAG resources loaded once during lifespan.
- `GET /health` returns `{"status":"ok"}` after successful startup.
- `POST /api/v1/query` returns `answer`, `references`, and `conversation_id`.
- Blank questions return `422`.
- API tests use fakes and do not call DeepSeek, Chroma, or BM25.
- CLI behavior remains intact.
- `conversation_id` is correlation-only; no code claims or implements multi-turn memory.
- Operational logs exist but do not persist full chat content, prompts, context, answers, secrets, or confidential company data.

## Deferred decisions

- Durable chat history and storage model.
- Real LangGraph checkpointer/memory and `conversation_id -> thread_id` semantics.
- Authentication and authorization.
- Streaming/SSE/WebSockets.
- Deployment packaging and production process manager.
- Moving or duplicating API concerns into `app/backend/` when the web application becomes a real separate backend.
