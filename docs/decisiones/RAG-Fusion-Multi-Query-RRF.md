# Plan de implementación — Multi-Query + RRF para RAG LangGraph

## Objetivo

Agregar un flujo experimental de recuperación Multi-Query con fusión Reciprocal Rank Fusion
(RRF) para comparar contra el flujo actual `rewrite_query → retrieve` sin reemplazarlo todavía.

La meta no es responder mejor por prompt, sino **mejorar la recuperación**: generar varias
consultas normativas alternativas, recuperar documentos por cada una y fusionar esas listas en
una sola lista `documents` compatible con el resto del grafo actual.

## Decisión principal

El flujo Multi-Query + RRF debe implementarse como **builder alterno**:

```text
build_langgraph_rag(...)              # flujo actual: rewrite_query simple + recuperación única
build_langgraph_rag_multiquery_rrf(...)  # flujo experimental: multi-query + RRF
```

No se elimina `rewrite_query_node` ni se cambia el flujo base. Esto mantiene comparación limpia
para evaluación: una sola variable experimental por corrida.

## Documentación revisada

- LangGraph documenta `Send` para fan-out/orchestrator-worker y reducers con
  `Annotated[..., operator.add]` para acumular escrituras concurrentes en listas.
- LangChain documenta invocación de modelos con `SystemMessage` / `HumanMessage` y
  `model.invoke(messages)`; en este proyecto se debe usar el wrapper local
  `core.llm.invoke_llm_text(...)` para conservar un punto único de extracción de texto.
- LangChain documenta structured output, pero este plan **no lo usa** por ahora: preferimos salida
  textual restringida + parser determinístico para evitar acoplar este experimento a Pydantic o
  function-calling antes de medir si Multi-Query aporta valor.

## Fuera de alcance

- No implementar reranking en este plan.
- No cambiar `LangChainRagResult`.
- No modificar `manual_implementation/`.
- No cambiar la ingesta/vectorización Chroma.
- No agregar guardrails.
- No tocar el flujo base salvo para reutilizar nodos/helpers en un builder alterno.

## Estructura de archivos

Crear/modificar solo estos archivos:

```text
agents/consulta_normativa/langchain_rag/
├── core/
│   ├── state.py                    # nuevos campos de estado
│   └── llm.py                      # se reutiliza invoke_llm_text
├── query_understanding/
│   ├── rewrite_query.py            # queda intacto como flujo base
│   └── multi_query.py              # nuevo: generación/parsing de variantes
├── retrieval/
│   └── fusion.py                   # nuevo: identidad documental + RRF
├── graph.py                        # nuevo builder alterno
└── config.py                       # parámetros del experimento
```

No crear carpeta `nodes/`: ya existe una estructura funcional por dimensión (`query_understanding/`,
`retrieval/`, `validation/`, etc.).

## Estado requerido

Modificar `RagGraphState` en `core/state.py`:

```python
from operator import add
from typing import Annotated

query_variants: list[str]
multi_query_trace: dict[str, Any]
retrieved_lists: Annotated[list[list[RetrievedDocument]], add]
```

`documents` ya existe y sigue siendo la salida final que consume el resto del grafo.

### Por qué `Annotated[..., add]`

Cuando LangGraph usa fan-out con `Send`, varias ramas pueden escribir en `retrieved_lists`. Sin
un reducer explícito, esas escrituras pueden pisarse. El reducer `operator.add` concatena las listas
escritas por cada rama.

## Identidad estable de documentos para RRF

`RetrievedDocument` hoy solo contiene:

```python
document: str
metadata: dict[str, Any]
```

No agregar `chunk_id` al modelo todavía. Para KISS, crear en `retrieval/fusion.py`:

```python
def document_identity(document: RetrievedDocument) -> str:
    ...
```

La identidad debe derivarse de metadata estable, en este orden:

1. si existe un ID explícito en metadata (`id`, `chunk_id` o equivalente), usarlo;
2. para tablas: usar `source_stem/source_document_id + table_key/table_index + table_part_index`;
3. para chunks: usar `source_stem/source_document_id + parent_id + start_char + end_char`;
4. fallback defensivo: combinar `reference_from_metadata(metadata)` + hash corto del texto.

El fallback evita fallos duros en tests o metadata incompleta, pero debe quedar trazado en tests
como caso menos confiable. Lo correcto en producción es que la metadata tenga trazabilidad.

## Prompt Multi-Query

Crear en `query_understanding/multi_query.py`:

```python
MULTI_QUERY_SYSTEM_PROMPT = """
Eres un componente de generación de consultas para recuperación normativa en un sistema RAG sobre
SG-SST colombiano.

Tu única tarea es generar consultas alternativas para recuperar mejor documentos normativos.

Corpus disponible:
- Decreto 768 de 2022
- Decreto 1072 de 2015, Libro 2, Título 4, Capítulo 6
- Ley 1010 de 2006
- Ley 1562 de 2012
- Resolución 0312 de 2019
- Resolución 1401 de 2007
- Resolución 2013 de 1986
- Resolución 2346 de 2007

Reglas estrictas:
- Conserva la intención original del usuario.
- Conserva cualquier ley, decreto, resolución, artículo, año, numeral o literal mencionado.
- No inventes normas, artículos, obligaciones, sanciones, cifras ni entidades.
- No respondas la pregunta.
- Genera consultas normativas breves en español, útiles para búsqueda semántica.
- Cada variante debe explorar un ángulo distinto de la misma necesidad: obligación, requisito,
  procedimiento, responsable, evidencia documental o estándar mínimo, según aplique.
- No repitas la pregunta original: el sistema la agregará por separado.
- No generes variantes triviales ni duplicadas.
- Devuelve solo las consultas, una por línea, sin numeración, comillas, viñetas ni explicación.
""".strip()
```

El prompt debe compartir intención con `QUERY_REWRITE_SYSTEM_PROMPT`, pero no importarlo ni componerlo
dinámicamente: mantener ambos prompts explícitos facilita revisión y evaluación por etapa.

## `query_understanding/multi_query.py`

Funciones a implementar:

```python
def build_multi_query_messages(question: str, max_variants: int) -> list[Any]:
    """Build lazy-imported LangChain messages for query variant generation."""


def parse_query_variants(raw_text: str, original_question: str, max_variants: int) -> list[str]:
    """Parse line-based model output into unique query variants."""


def generate_query_variants_node(llm: Any, max_variants: int) -> Callable[[RagGraphState], RagGraphState]:
    """Generate query variants; always include the original question at position 0."""
```

Reglas del nodo:

- Si `question.strip()` está vacío: `query_variants = [question]` y `fallback=True`.
- Invocar el LLM con `invoke_llm_text(llm, messages)`.
- Parsear salida por líneas.
- Quitar numeración simple si el modelo la desobedece (`1.`, `-`, `*`).
- Deduplicar preservando orden.
- Excluir variantes iguales a la pregunta original.
- Limitar a `MULTI_QUERY_MAX_VARIANTS`.
- Devolver siempre `[original_question, *variants]`.
- Si el LLM falla o no produce variantes válidas, usar `[original_question]`.

Trazabilidad mínima:

```python
"multi_query_trace": {
    "variant_count": len(query_variants),
    "generated_count": len(query_variants) - 1,
    "fallback": bool,
    "error": None | str,
}
```

## `retrieval/fusion.py`

Funciones a implementar:

```python
def retrieve_variant_node(retriever: Retriever, top_k: int) -> Callable[[dict[str, Any]], RagGraphState]:
    """Retrieve and normalize documents for one query variant."""


def fanout_retrieve_variants(state: RagGraphState) -> list[Send]:
    """Create one retrieval worker per query variant."""


def document_identity(document: RetrievedDocument) -> str:
    """Return a stable identity for RRF deduplication."""


def reciprocal_rank_fusion(ranked_lists: list[list[RetrievedDocument]], k: int) -> list[RetrievedDocument]:
    """Fuse ranked lists using RRF score: 1 / (k + one_based_rank)."""


def rrf_fuse_node(rrf_k: int, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    """Fuse retrieved lists and write final normalized documents."""
```

Nota técnica: usar rank one-based para la fórmula:

```python
score += 1 / (rrf_k + rank)
```

donde `rank` empieza en `1`, no en `0`. Esto evita favorecer excesivamente el primer resultado.

## Configuración

Agregar a `config.py`:

```python
MULTI_QUERY_MAX_VARIANTS = 3
MULTI_QUERY_TOP_K_PER_VARIANT = DEFAULT_TOP_K
RRF_K = 60
MULTIQUERY_RRF_TOP_K = DEFAULT_TOP_K
```

Decisión conservadora: `MULTIQUERY_RRF_TOP_K = DEFAULT_TOP_K` mientras no haya reranker. Si luego se
conecta reranking, se puede subir a 15-20 para entregar más candidatos al reranker.

## Wiring del grafo experimental

Agregar en `graph.py`:

```python
def build_langgraph_rag_multiquery_rrf(llm: Any, retriever: Retriever) -> Any:
    ...
```

Flujo:

```text
generate_query_variants
  → fan-out retrieve_variant por cada query
  → rrf_fuse
  → record_retrieval_trace
  → evidence_route
      ├── sin evidencia → fallback_answer → format_result
      └── con evidencia → format_context → build_messages → generate_answer → format_result
```

No pasar por `normalize_documents_node`, porque cada rama ya normaliza con `recovered_documents`.

## Relación con reranking

Conservar estas decisiones del plan `Reranking.md`, pero no implementarlas aquí:

- El reranker debe insertarse después de `rrf_fuse` y antes de `evidence_route`.
- Modelo candidato: `BAAI/bge-reranker-v2-m3`, por ser multilingüe y local.
- El reranking evita consumo de Groq, pero añade latencia y descarga local grande; medir antes de
  fijarlo como default.
- Si se encadena reranking, subir `MULTIQUERY_RRF_TOP_K` a un pool de 15-20 candidatos.

## Tests requeridos

Crear:

```text
agents/consulta_normativa/tests/test_langchain_rag_multi_query.py
agents/consulta_normativa/tests/test_langchain_rag_fusion.py
```

Casos mínimos:

### Multi-Query

- Construye mensajes con imports perezosos de `langchain_core.messages`.
- Parser acepta salida por líneas y elimina numeración/viñetas simples.
- Parser deduplica variantes y excluye la pregunta original.
- Nodo exitoso devuelve `[original_question, *variants]`.
- Error o salida vacía hace fallback a `[original_question]` con trace.

### RRF

- `document_identity` usa trazabilidad estable para chunks.
- `document_identity` usa identidad lógica para tablas.
- `reciprocal_rank_fusion` fusiona listas con duplicados y preserva un solo documento por identidad.
- Un documento repetido en varias listas sube de posición.
- `rrf_fuse_node` escribe `documents`, no otro campo.

### Grafo experimental

- `build_langgraph_rag(...)` base no cambia.
- `build_langgraph_rag_multiquery_rrf(...)` recupera por cada variante generada.
- El retriever recibe variantes, no solo la pregunta original.
- La salida final sigue siendo `LangChainRagResult`.
- Tests fake-based: sin Groq real, sin Chroma real.

## Verificación

```bash
python -m unittest \
  agents.consulta_normativa.tests.test_langchain_rag_multi_query \
  agents.consulta_normativa.tests.test_langchain_rag_fusion \
  agents.consulta_normativa.tests.test_langchain_rag_graph \
  agents.consulta_normativa.tests.test_langchain_rag_llm \
  agents.consulta_normativa.tests.test_langchain_rag_query_rewrite
```

```bash
python -m compileall agents/consulta_normativa/langchain_rag agents/consulta_normativa/tests
```

## Criterios de aceptación

- El flujo base actual sigue funcionando y no cambia su wiring.
- Existe builder alterno `build_langgraph_rag_multiquery_rrf(...)`.
- Multi-Query usa `core.llm.invoke_llm_text`, no `with_structured_output`.
- Multi-Query devuelve variantes normativas, breves, en español y sin respuesta final.
- RRF es determinístico, local y sin LLM.
- RRF deduplica por identidad estable derivada de metadata.
- El resultado fusionado se escribe en `state["documents"]`.
- No se implementa reranking en este plan.
- No hay llamadas reales a Groq ni Chroma en tests.

## Decisiones pendientes antes de implementar

1. Confirmar si el builder experimental debe exponerse desde `__init__.py` ahora o solo cuando se
   conecte a un CLI/runner de experimentos.
2. Confirmar si `MULTIQUERY_RRF_TOP_K` queda igual a `DEFAULT_TOP_K` para esta primera evaluación.
3. Confirmar si la comparación se hará manualmente por tests/CLI o mediante un runner específico
   de experimentos más adelante.
