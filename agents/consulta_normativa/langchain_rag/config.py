"""Runtime defaults for the normative consultation agent."""

from pathlib import Path

from agents.shared.chroma_retrieval import DEFAULT_COLLECTION_NAME


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CHROMA_PATH = PROJECT_ROOT / "data" / "processed" / "chroma"
DEFAULT_TOP_K = 3
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 0

# Multi-Query implementation.
MULTI_QUERY_MAX_VARIANTS = 3                       # Número de variantes de la consulta a generar.
MULTI_QUERY_TOP_K_PER_VARIANT = DEFAULT_TOP_K      # Número de documentos a recuperar por variante.
RRF_K = 60                                         # K representa el coeficiente de ponderación para Reciprocal Rank Fusion. Un valor más alto da más peso a los documentos que aparecen en los primeros puestos de las listas de resultados.
# Dejar Default_Top_K no conviene
MULTIQUERY_RRF_TOP_K = DEFAULT_TOP_K               # Número de documentos a recuperar después de la fusión RRF.
