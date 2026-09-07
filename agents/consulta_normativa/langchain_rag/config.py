"""Runtime defaults for the normative consultation agent."""

from pathlib import Path

from agents.consulta_normativa.langchain_rag.retrieval.chroma_retrieval import DEFAULT_COLLECTION_NAME
from pipeline.chunking.core.config import DEFAULT_PARENT_CHUNKS_PATH


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CHROMA_PATH = PROJECT_ROOT / "data" / "processed" / "chroma"

# Por que son iguales?
RETRIEVAL_TOP_K = 8
DEFAULT_TOP_K = RETRIEVAL_TOP_K

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_TEMPERATURE = 0

# Multi-Query implementation.
MULTI_QUERY_MAX_VARIANTS = 4        # Número de variantes de la consulta a generar.
MULTI_QUERY_TOP_K_PER_VARIANT = 3   # Número de documentos a recuperar por variante.

# Reciprocal Rank Fusion.
RRF_K = 60                              # K representa el coeficiente de ponderación para Reciprocal Rank Fusion. Un valor más alto da más peso a los documentos que aparecen en los primeros puestos de las listas de resultados.
MULTIQUERY_RRF_TOP_K = DEFAULT_TOP_K    # Número de documentos a recuperar después de la fusión RRF.

# Hybrid Retrieval.
HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = RRF_K

# Reranking with Cross-Encoder.
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"    # Modelo de re-ranking con Cross-Encoder.
RERANKER_MAX_LENGTH = 512                          # Longitud máxima (tokens) de los documentos a procesar por el modelo.
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K               # Número de documentos a recuperar después del re-ranking.

# Este cambia acorde la tecnica elegida para mejorar la consulta.
RERANKER_CANDIDATE_POOL_SIZE = 40   # Número de documentos candidatos a recuperar para el re-ranking.
