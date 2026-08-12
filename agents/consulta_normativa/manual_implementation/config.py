"""Runtime defaults for the normative consultation agent."""

from pathlib import Path

from agents.shared.chroma_retrieval import DEFAULT_COLLECTION_NAME


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CHROMA_PATH = PROJECT_ROOT / "data" / "processed" / "chroma"
DEFAULT_TOP_K = 5
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 0
