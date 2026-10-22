"""Download the pinned Hugging Face models into HF_HOME during the image build."""

import ast
import sys
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EMBEDDING_CONFIG = Path("pipeline/chunking/config.py")
RERANKER_CONFIG = Path("agents/consulta_normativa/langchain_rag/config.py")


class PinnedModelError(ValueError):
    """Raised when a pinned model constant cannot be read from a config file."""


def read_constant(path: Path, name: str) -> str:
    """Return a module-level string constant without importing the module."""

    # Parsed with ast so this build layer only depends on the two config files.
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
            raise PinnedModelError(f"{name} in {path} is not a string literal")
    raise PinnedModelError(f"{name} is not defined in {path}")


def pinned_models(root: Path) -> tuple[tuple[str, str], ...]:
    """Return the (repo_id, revision) pairs loaded by the online runtime."""

    embedding_config = root / EMBEDDING_CONFIG
    reranker_config = root / RERANKER_CONFIG
    return (
        (
            read_constant(embedding_config, "DEFAULT_EMBEDDING_MODEL"),
            read_constant(embedding_config, "DEFAULT_EMBEDDING_MODEL_REVISION"),
        ),
        (
            read_constant(reranker_config, "RERANKER_MODEL_NAME"),
            read_constant(reranker_config, "RERANKER_MODEL_REVISION"),
        ),
    )


def main(root: Path = PROJECT_ROOT, download: Callable[..., str] | None = None) -> int:
    """Download every pinned model snapshot and return the process exit code."""

    if download is None:
        from huggingface_hub import snapshot_download

        download = snapshot_download

    for repo_id, revision in pinned_models(root):
        path = download(repo_id=repo_id, revision=revision)
        print(f"Downloaded {repo_id}@{revision} to {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
