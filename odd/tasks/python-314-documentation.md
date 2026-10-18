# Python 3.14 documentation update

## Objective

Make Python 3.14 the official supported Python version in the active project documentation.

## Scope

- Update active Python 3.12 policy references in `plan-docker.md`, `GUIA_EJECUCION_BACKEND.md`, and `docs/testing.md` to Python 3.14.
- Ensure commands that explicitly select the virtual-environment interpreter use `python3.14 -m venv`.
- Compare the supplied Python 3.14 environment evidence with `requirements.txt` without changing dependency declarations.
- Preserve unrelated historical records and runtime evidence.

## Constraints

- Documentation-only change within the four allowed Markdown files.
- Do not modify code, `requirements.txt`, `.python-version`, Docker/CI artifacts, or secrets.
- Do not create a commit.
- Declare only Python major.minor policy; do not document a Python 3.14 patch version.

## Verification

- [x] Confirm active Python policy references in the three target documents use Python 3.14.
- [x] Confirm explicit interpreter-selected venv commands use `python3.14 -m venv`.
- [x] Compare direct requirements with the supplied installed-package evidence.
- [x] Run Markdown/content checks.
- [x] Run `git diff --check`.
- [x] Confirm only allowed Markdown files were edited by this task.

## Dependency comparison

The supplied Python 3.14 environment evidence contains every direct requirement currently declared in `requirements.txt`.

### Unpinned or range-constrained direct requirements

| Requirement | Installed evidence |
|---|---:|
| `langchain-openai` | `1.6.0` |
| `pydantic>=2,<3` | `2.13.4` |
| `fastapi` | `0.141.1` |
| `uvicorn` | `0.52.1` |
| `httpx` | `0.28.1` |
| `chromadb` | `1.5.9` |
| `bm25s` | `0.3.11` |
| `reportlab` | `5.0.1` |
| `pytest` | `9.1.1` |

### Pinned direct requirements matching installed evidence

| Requirement | Installed evidence | Result |
|---|---:|---|
| `langchain-text-splitters==1.1.2` | `1.1.2` | Match |
| `langchain-experimental==0.4.2` | `0.4.2` | Match |
| `langchain-huggingface==1.2.2` | `1.2.2` | Match |
| `langchain==1.1.2` | `1.1.2` | Match |
| `langgraph==1.0.4` | `1.0.4` | Match |
| `langchain-groq==1.0.0` | `1.0.0` | Match |
| `python-dotenv==1.2.1` | `1.2.1` | Match |
| `pypandoc==1.17` | `1.17` | Match |
| `sentence-transformers==5.6.0` | `5.6.0` | Match |
| `tiktoken==0.13.0` | `0.13.0` | Match |
| `pillow==12.3.0` | `12.3.0` | Match |

`chromadb`, `bm25s`, and `pytest` are present at versions `1.5.9`, `0.3.11`, and `9.1.1`, respectively.

### Observed non-direct packages

The environment also contains transitive dependencies and environment tooling not declared directly in `requirements.txt`. Their presence in `pip list` is not sufficient evidence to copy them into the manifest. Direct-use evidence must be established first.

Observed non-direct packages include the `aiohttp` stack; FastAPI/Starlette/AnyIO; LangChain and LangGraph support packages; OpenAI and Groq SDK dependencies; ChromaDB's gRPC, Kubernetes, OpenTelemetry, ONNX, and storage dependencies; Sentence Transformers' NumPy, SciPy, scikit-learn, PyTorch, Transformers, tokenizers, and NVIDIA/CUDA dependencies; HTTP, serialization, validation, and packaging utilities; and environment tools such as `pip`, `setuptools`, and build hooks.

## Validation results

- Python policy/content check: passed; no active `3.12` reference remains in the three target documents.
- Version-policy check: passed; project documentation declares major.minor `3.14`, not a patch release.
- Virtual-environment command check: passed; the explicit command is `python3.14 -m venv .venv-rag`.
- Markdown fenced-block check: passed.
- Requirements comparison: passed; all 20 direct declarations were found in the supplied installed-package evidence, and all 11 exact pins match.
- `git diff --check`: passed.
- Scope check: passed; this task edited only the four allowed Markdown files. Pre-existing unrelated worktree changes were preserved.
- Commit: not created, by policy.
- Skill resolution: `paths-injected`.
