# DeepSeek LLM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default LangGraph RAG generator from Groq `ChatGroq` to DeepSeek through LangChain's OpenAI-compatible `ChatOpenAI` integration.

**Architecture:** Keep the RAG graph provider-agnostic: retrieval, reranking, validation nodes, and `invoke_llm_text()` continue receiving a LangChain-like `llm`. Limit provider-specific logic to configuration, LLM construction, runtime dependency naming, tests, and docs. Keep `build_groq_llm()` temporarily as a compatibility helper unless the user explicitly requests full removal.

**Tech Stack:** Python, LangChain, `langchain-openai`, DeepSeek OpenAI-compatible API, `unittest`.

## Global Constraints

- Do not modify retrieval, vectorization, sparse indexing, reranking, graph topology, prompts, or validation technique behavior.
- Do not hardcode API keys. Use `DEEPSEEK_API_KEY` from the environment.
- DeepSeek API base URL: `https://api.deepseek.com`.
- Default model for this migration: `deepseek-chat`.
- Keep `DEFAULT_TEMPERATURE = 0`.
- Use `python -m unittest`, not pytest.
- Generated technical artifacts/code/comments/tests default to English.
- Preserve KISS/YAGNI: no provider registry, no CLI provider switch, no multi-provider abstraction unless a test seam needs a small rename.

---

## External documentation checked

- DeepSeek API is OpenAI-compatible and can be called with the OpenAI SDK using `base_url="https://api.deepseek.com"` and `DEEPSEEK_API_KEY`.
- LangChain supports OpenAI-compatible providers through `langchain_openai.ChatOpenAI(base_url=..., api_key=..., model=...)`.
- DeepSeek exposes chat models such as `deepseek-chat`; reasoning models may exist, but this migration should start with chat mode for predictable RAG latency and behavior.

## Current code baseline

- `agents/consulta_normativa/langchain_rag/core/llm.py` currently defines `build_groq_llm()` and imports `ChatGroq` lazily.
- `agents/consulta_normativa/langchain_rag/config.py` currently defines `DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"` and `DEFAULT_TEMPERATURE = 0`.
- `agents/consulta_normativa/langchain_rag/main.py` wires `RuntimeDependencies.build_groq_llm` and calls it inside `build_runtime()`.
- The graph already accepts a generic `llm`, so `graph.py` should not need changes.

---

## Task 1: Add the DeepSeek dependency

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces import availability for `from langchain_openai import ChatOpenAI`.

- [ ] **Step 1: Add dependency**

Add:

```txt
langchain-openai
```

Do not remove `langchain-groq` in this task. Removal is a separate cleanup decision after DeepSeek is verified.

- [ ] **Step 2: Verify dependency import after install**

Run after installing requirements:

```bash
python -c "from langchain_openai import ChatOpenAI; print(ChatOpenAI.__name__)"
```

Expected: prints `ChatOpenAI`.

---

## Task 2: Add DeepSeek runtime config

**Files:**
- Modify: `agents/consulta_normativa/langchain_rag/config.py`

**Interfaces:**
- Produces `DEFAULT_DEEPSEEK_MODEL: str`.
- Produces `DEEPSEEK_BASE_URL: str`.
- Existing `DEFAULT_TEMPERATURE` remains unchanged.

- [ ] **Step 1: Add constants**

Add near the current model defaults:

```python
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
```

Keep `DEFAULT_GROQ_MODEL` for now so old tests/imports do not break unnecessarily.

- [ ] **Step 2: Verify config import**

Run:

```bash
python - <<'PY'
from agents.consulta_normativa.langchain_rag.config import DEFAULT_DEEPSEEK_MODEL, DEEPSEEK_BASE_URL
print(DEFAULT_DEEPSEEK_MODEL, DEEPSEEK_BASE_URL)
PY
```

Expected: `deepseek-chat https://api.deepseek.com`.

---

## Task 3: Implement `build_deepseek_llm()`

**Files:**
- Modify: `agents/consulta_normativa/langchain_rag/core/llm.py`
- Test: `agents/consulta_normativa/tests/test_langchain_rag_llm.py`

**Interfaces:**
- Produces `build_deepseek_llm() -> Any`.
- Consumes environment variable `DEEPSEEK_API_KEY`.
- Returns a LangChain chat model compatible with `.invoke(...)` and `.with_structured_output(...)`.

- [ ] **Step 1: Write failing test for missing API key**

Add a test equivalent to:

```python
def test_build_deepseek_llm_requires_api_key(self) -> None:
    with patch.dict(os.environ, {}, clear=True):
        with self.assertRaises(ValueError) as context:
            build_deepseek_llm()

    self.assertIn("DEEPSEEK_API_KEY is not configured", str(context.exception))
```

- [ ] **Step 2: Write failing test for missing dependency**

Patch `sys.modules` so `langchain_openai` is unavailable and assert a controlled `ModuleNotFoundError`:

```python
def test_build_deepseek_llm_reports_missing_langchain_openai(self) -> None:
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
        with patch.dict(sys.modules, {"langchain_openai": None}):
            with self.assertRaises(ModuleNotFoundError) as context:
                build_deepseek_llm()

    self.assertIn("langchain_openai is not installed", str(context.exception))
```

- [ ] **Step 3: Write failing test for constructor arguments**

Patch a fake `ChatOpenAI` and assert the exact arguments:

```python
def test_build_deepseek_llm_uses_deepseek_openai_compatible_endpoint(self) -> None:
    calls = []

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    fake_module = types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI)

    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
        with patch.dict(sys.modules, {"langchain_openai": fake_module}):
            llm = build_deepseek_llm()

    self.assertIsInstance(llm, FakeChatOpenAI)
    self.assertEqual(calls, [{
        "model": DEFAULT_DEEPSEEK_MODEL,
        "api_key": "test-key",
        "base_url": DEEPSEEK_BASE_URL,
        "temperature": DEFAULT_TEMPERATURE,
    }])
```

- [ ] **Step 4: Implement function**

Update imports in `core/llm.py`:

```python
from agents.consulta_normativa.langchain_rag.config import (
    DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_TEMPERATURE,
)
```

Add:

```python
def build_deepseek_llm() -> Any:
    """Build the default DeepSeek LangChain chat model lazily."""

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured in the environment.")

    try:
        # pyrefly: ignore [missing-import]
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langchain_openai is not installed: {error}") from error

    return ChatOpenAI(
        model=DEFAULT_DEEPSEEK_MODEL,
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
        temperature=DEFAULT_TEMPERATURE,
    )
```

Leave `build_groq_llm()` in place for compatibility during this migration.

- [ ] **Step 5: Run LLM tests**

Run:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_llm
```

Expected: PASS.

---

## Task 4: Switch LangGraph runtime from Groq to DeepSeek

**Files:**
- Modify: `agents/consulta_normativa/langchain_rag/main.py`
- Test: whichever test file currently covers runtime dependency loading, or add coverage to `agents/consulta_normativa/tests/test_langchain_rag_main.py` if present.

**Interfaces:**
- Replace `RuntimeDependencies.build_groq_llm` with `RuntimeDependencies.build_deepseek_llm`.
- `build_runtime()` calls `dependencies.build_deepseek_llm()`.

- [ ] **Step 1: Rename runtime dependency field**

Change:

```python
build_groq_llm: Callable[[], Any]
```

to:

```python
build_deepseek_llm: Callable[[], Any]
```

- [ ] **Step 2: Change runtime construction**

Change:

```python
llm = dependencies.build_groq_llm()
```

to:

```python
llm = dependencies.build_deepseek_llm()
```

- [ ] **Step 3: Change lazy dependency import**

Change:

```python
from agents.consulta_normativa.langchain_rag.core.llm import build_groq_llm
```

to:

```python
from agents.consulta_normativa.langchain_rag.core.llm import build_deepseek_llm
```

And return:

```python
build_deepseek_llm=build_deepseek_llm,
```

- [ ] **Step 4: Update docstrings/messages that say Groq-backed**

Change runtime-only wording such as:

```python
"Build the hybrid retriever and Groq-backed LLM for the session."
```

to:

```python
"Build the hybrid retriever and DeepSeek-backed LLM for the session."
```

Do not change unrelated docs in this task.

- [ ] **Step 5: Add/update main tests**

If `test_langchain_rag_main.py` has dependency fakes, update them to expose `build_deepseek_llm` instead of `build_groq_llm`.

Add a test equivalent to:

```python
def test_build_runtime_uses_deepseek_llm_builder(self) -> None:
    calls = []

    def build_deepseek_llm():
        calls.append("deepseek")
        return object()

    # Use the existing runtime dependency patching pattern in this test file.
    # Assert calls == ["deepseek"] after build_runtime().
```

- [ ] **Step 6: Run main tests**

Run:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main
```

Expected: PASS.

---

## Task 5: Verify structured-output compatibility path

**Files:**
- No production file changes unless tests reveal a real issue.
- Test: validation tests already using `.with_structured_output(...)`.

**Interfaces:**
- DeepSeek model object returned through `ChatOpenAI` must support `.with_structured_output(...)` for validation modules.

- [ ] **Step 1: Run unit tests for validation modules**

Run:

```bash
python -m unittest agents.consulta_normativa.tests.test_self_refine
python -m unittest agents.consulta_normativa.tests.test_retrieval_relevance_grading
python -m unittest agents.consulta_normativa.tests.test_sufficient_context_gate
```

Expected: PASS in local fake/unit tests.

- [ ] **Step 2: Run one real smoke test with API key**

Only run after the user has exported the key locally:

```bash
export DEEPSEEK_API_KEY="..."
python -m agents.consulta_normativa.langchain_rag.main "¿Qué exige la Resolución 0312 de 2019 para una empresa de riesgo I?"
```

Expected:

- initialization does not ask for `GROQ_API_KEY`;
- no `langchain_openai is not installed` error;
- graph returns a `LangChainRagResult`;
- answer is printed with references when retrieval succeeds.

If this fails specifically inside `.with_structured_output(...)`, record the provider limitation and stop. Do not implement a custom parser in the same pass.

---

## Task 6: Update operational documentation minimally

**Files:**
- Modify the smallest relevant operations/readme doc that currently tells users to set `GROQ_API_KEY`, if present.
- Likely candidates: `docs/operations/` or existing RAG usage guide.

**Interfaces:**
- User-facing run command should now mention `DEEPSEEK_API_KEY`.

- [ ] **Step 1: Locate current Groq setup docs**

Use content search for `GROQ_API_KEY` and `ChatGroq`.

- [ ] **Step 2: Replace runtime setup instruction**

Change:

```bash
export GROQ_API_KEY="..."
```

to:

```bash
export DEEPSEEK_API_KEY="..."
```

Mention default model:

```text
Default generator model: deepseek-chat through https://api.deepseek.com.
```

Do not rewrite broader methodology docs.

---

## Task 7: Final verification

Run focused tests:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_llm
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main
python -m unittest agents.consulta_normativa.tests.test_self_refine agents.consulta_normativa.tests.test_retrieval_relevance_grading agents.consulta_normativa.tests.test_sufficient_context_gate
python -m compileall agents/consulta_normativa/langchain_rag agents/shared
```

Run broad vector/RAG suite if time allows:

```bash
python -m unittest agents.consulta_normativa.tests.test_cli agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_langchain_rag_graph agents.consulta_normativa.tests.test_langchain_rag_query_rewrite agents.consulta_normativa.tests.test_langchain_rag_multi_query agents.consulta_normativa.tests.test_langchain_rag_fusion
```

## Acceptance criteria

- Runtime uses `DEEPSEEK_API_KEY`, not `GROQ_API_KEY`.
- Runtime constructs `ChatOpenAI(model="deepseek-chat", base_url="https://api.deepseek.com", temperature=0)`.
- Graph code remains provider-agnostic and unchanged unless tests reveal a real contract issue.
- Validation modules using `.with_structured_output(...)` still pass their unit tests.
- CLI initialization errors mention DeepSeek setup, not Groq setup.
- Documentation/runbook no longer tells the user to configure Groq for the LangGraph runtime.

## Risks to watch

- `ChatOpenAI.with_structured_output(...)` may behave differently against DeepSeek's OpenAI-compatible endpoint than against OpenAI itself. Smoke-test the validation modules with the real API before trusting runtime validation.
- DeepSeek reasoning models can change latency/cost significantly. Start with `deepseek-chat`; evaluate `deepseek-reasoner` separately.
- Long-context availability does not remove the need for retrieval quality. Keep parent expansion and context observability in place.
- Do not remove Groq code until DeepSeek has passed at least one real end-to-end RAG smoke test.
