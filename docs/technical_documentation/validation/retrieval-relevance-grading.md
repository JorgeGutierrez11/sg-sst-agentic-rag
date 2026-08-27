# Retrieval Relevance Grading para validación de evidencia normativa

Retrieval Relevance Grading es una técnica experimental de validación posterior a la recuperación. Evalúa individualmente los documentos recuperados por el RAG y elimina aquellos que no aportan evidencia útil para responder la pregunta original del usuario antes de construir el contexto enviado al LLM.

La implementación toma como referencia el concepto de *retrieval evaluator* utilizado en Corrective Retrieval-Augmented Generation (CRAG), pero no implementa la arquitectura CRAG completa.

## Propósito

El baseline del RAG considera que existe evidencia siempre que el retriever devuelva al menos un documento. Este criterio permite que documentos semánticamente cercanos pero irrelevantes lleguen al generador.

Retrieval Relevance Grading introduce una evaluación explícita entre recuperación y generación:

```text
documento recuperado + pregunta original
                    ↓
             relevance grader
                    ↓
            relevante / irrelevante
```

El objetivo es reducir ruido en el contexto y evitar que la mera existencia de resultados de Chroma sea interpretada como evidencia válida.

La técnica evalúa **relevancia**, no suficiencia. Un documento puede considerarse relevante aunque solo permita responder una parte de la pregunta o necesite complementarse con otros fragmentos.

## Ubicación en el pipeline LangGraph

Para evaluar la técnica de forma aislada, el flujo experimental se construye sobre el retrieval base:

```text
question
   ↓
retrieve
   ↓
normalize_documents
   ↓
record_retrieval_trace
   ↓
grade_retrieval_relevance
   ↓
evidence_route
   ├── with_evidence ──→ format_context
   │                     ↓
   │                build_messages
   │                     ↓
   │                generate_answer
   │
   └── without_evidence → fallback_answer
                              ↓
                         format_result
```

`record_retrieval_trace` se ejecuta antes del grader para conservar información sobre los documentos originalmente recuperados. Posteriormente, `grade_retrieval_relevance` modifica `state["documents"]` y deja únicamente los documentos aceptados.

`evidence_route` no necesita modificarse: después del filtrado, una lista vacía implica que ninguno de los documentos fue considerado utilizable.

Archivos principales:

* `agents/consulta_normativa/langchain_rag/validation/retrieval_relevance_grading.py`
* `agents/consulta_normativa/langchain_rag/graph.py`
* `agents/consulta_normativa/langchain_rag/core/state.py`
* `agents/consulta_normativa/tests/test_retrieval_relevance_grading.py`

## Resumen de implementación

La técnica se divide en las siguientes piezas:

| Pieza                                   | Responsabilidad                                                                                                   |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `RelevanceGrade`                        | Define mediante Pydantic la salida estructurada del grader: decisión booleana y justificación.                    |
| `RETRIEVAL_RELEVANCE_SYSTEM_PROMPT`     | Define qué significa relevancia dentro del dominio normativo SG-SST y separa relevancia de suficiencia.           |
| `retrieval_relevance_grading_node(llm)` | Construye el nodo LangGraph, evalúa cada documento, filtra los irrelevantes y genera la traza.                    |
| `grade_document_relevance(...)`         | Invoca el grader para un único par pregunta-documento y valida la salida estructurada.                            |
| `build_relevance_grading_messages(...)` | Construye los mensajes enviados al LLM usando la pregunta original, metadata normativa y contenido del documento. |
| `format_relevance_metadata(...)`        | Selecciona metadata normativa útil para apoyar la decisión del grader.                                            |
| `build_document_trace(...)`             | Registra la decisión, motivo, fuente, artículo, fallback y error de cada documento.                               |
| `relevance_grading_fallback(...)`       | Conserva los documentos cuando no puede inicializarse el grader estructurado.                                     |

## Salida estructurada

El grader utiliza Pydantic para impedir que la lógica del grafo dependa de texto libre:

```python
class RelevanceGrade(BaseModel):
    relevant: bool
    reason: str
```

Los campos tienen las siguientes funciones:

| Campo      | Uso                                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| `relevant` | Indica si el documento aporta evidencia directamente relacionada con al menos una parte de la pregunta. |
| `reason`   | Explicación breve de la decisión basada exclusivamente en la pregunta y el documento recuperado.        |

No se utiliza un score numérico de relevancia. La decisión es binaria para evitar introducir umbrales sobre puntuaciones de LLM no calibradas.

## Criterio de relevancia

El grader considera un documento **relevante** cuando contiene información normativa que contribuye directamente a responder al menos una parte de la pregunta.

Puede seguir siendo relevante aunque:

* no permita responder completamente la consulta;
* responda únicamente uno de varios elementos solicitados;
* necesite complementarse con otros documentos;
* corresponda a un fragmento parcial de una disposición normativa.

Un documento se considera **no relevante** cuando:

* únicamente comparte vocabulario general relacionado con SG-SST;
* contiene palabras presentes en la pregunta pero no aporta evidencia útil;
* trata una obligación, sujeto, procedimiento o situación distinta;
* pertenece a la misma norma consultada, pero el fragmento concreto no contribuye a responder;
* su relación con la pregunta depende de información que no aparece en el fragmento.

Esta separación es importante porque Retrieval Relevance Grading no determina si el contexto completo es suficiente para responder. Esa responsabilidad corresponde a una técnica posterior de `Answerability / Sufficient-Context Gate`.

## Pregunta usada para la evaluación

El grader utiliza:

```python
state["question"]
```

y no:

```python
state["retrieval_query"]
```

La decisión se toma contra la necesidad original expresada por el usuario.

Esto evita que un error introducido por una técnica previa de transformación de consulta se propague también al mecanismo de validación.

## Evaluación individual de documentos

Los documentos se califican individualmente:

```text
documents = [D1, D2, D3, D4, D5]

D1 → relevante
D2 → irrelevante
D3 → relevante
D4 → irrelevante
D5 → relevante

documents final = [D1, D3, D5]
```

Evaluar cada documento por separado permite eliminar evidencia ruidosa sin descartar un conjunto completo porque algunos de sus elementos sean irrelevantes.

Los nodos posteriores continúan usando el contrato existente:

```python
state["documents"]
```

No se crea un campo separado como `relevant_documents`.

## Metadata entregada al grader

Además del texto del documento, el grader puede recibir metadata normativa seleccionada:

* fuente;
* tipo normativo;
* año;
* título;
* capítulo;
* artículo;
* parágrafo;
* numeral;
* literal.

La metadata se utiliza como información auxiliar para interpretar correctamente el fragmento. No reemplaza el contenido documental ni hace que un fragmento sea relevante por pertenecer a una norma determinada.

## Decisiones y guardrails importantes

| Aspecto                     | Implementación actual                                                                                                      |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Unidad evaluada             | Cada `RetrievedDocument` se evalúa individualmente.                                                                        |
| Pregunta utilizada          | Se utiliza `state["question"]`, es decir, la pregunta original del usuario.                                                |
| Salida del LLM              | `RelevanceGrade` mediante `with_structured_output(...)`.                                                                   |
| Relevancia vs. suficiencia  | El prompt prohíbe decidir si el documento responde completamente la pregunta.                                              |
| Uso de conocimiento externo | El grader debe decidir únicamente a partir de la pregunta y el documento recibido.                                         |
| Coincidencia léxica         | Compartir términos de SG-SST no es suficiente para considerar relevante un fragmento.                                      |
| Documento relevante         | Se conserva en `state["documents"]`.                                                                                       |
| Documento irrelevante       | Se elimina antes de construir el contexto.                                                                                 |
| Error del grader            | Política `fail-open`: el documento se conserva para evitar descartar evidencia potencialmente válida por un fallo técnico. |
| Reintentos                  | La implementación actual no realiza retries.                                                                               |
| Observabilidad              | Cada decisión conserva `relevant`, `reason`, `fallback`, `error`, fuente y artículo.                                       |
| CRAG                        | Se implementa únicamente relevance grading inspirado en el retrieval evaluator de CRAG; no CRAG completo.                  |

## Campos de estado

| Campo                     | Uso                                                                     |
| ------------------------- | ----------------------------------------------------------------------- |
| `question`                | Pregunta original contra la cual se evalúa cada documento.              |
| `documents`               | Documentos recuperados de entrada y documentos aceptados de salida.     |
| `retrieval_traces`        | Información registrada antes del grader sobre la recuperación original. |
| `relevance_grading_trace` | Traza de decisiones realizadas por el grader.                           |

`relevance_grading_trace` contiene información agregada y decisiones por documento:

```python
{
    "input_count": 5,
    "relevant_count": 3,
    "rejected_count": 2,
    "fallback_count": 0,
    "documents": [
        {
            "index": 0,
            "chroma_id": "...",
            "source": "Resolución 1401 de 2007",
            "article": "6°",
            "relevant": True,
            "reason": "...",
            "fallback": False,
            "error": None,
        }
    ],
}
```

En la implementación actual, los documentos conservados mediante `fail-open` también forman parte de `documents` y del conteo de documentos aceptados. Por ello, `fallback_count` debe utilizarse para distinguir decisiones positivas del grader de documentos preservados debido a errores técnicos.

## Fallos y comportamiento fallback

La técnica utiliza una política conservadora de tipo `fail-open`.

### Fallo al inicializar structured output

Si:

```python
llm.with_structured_output(RelevanceGrade)
```

produce una excepción, la técnica conserva todos los documentos recuperados.

Conceptualmente:

```text
grader no disponible
        ↓
conservar documentos originales
        ↓
continuar pipeline
```

La traza registra:

```python
{
    "fallback": True,
    "error": type(error).__name__,
    ...
}
```

### Fallo al evaluar un documento

Si falla únicamente la evaluación de un documento:

```text
D1 → relevante
D2 → ERROR
D3 → irrelevante
```

el resultado es:

```text
D1 → conservar
D2 → conservar por fail-open
D3 → eliminar
```

La decisión sobre `D2` queda registrada como:

```python
{
    "relevant": True,
    "fallback": True,
    "reason": "Documento conservado por política fail-open debido a un error del grader.",
    "error": "...",
}
```

Un error técnico del evaluador no se interpreta como evidencia de irrelevancia.

## Routing posterior

La técnica reutiliza `evidence_route`.

Después del filtrado:

```python
state["documents"] = relevant_documents
```

Si la lista contiene al menos un documento:

```text
with_evidence → format_context
```

Si todos los documentos fueron rechazados:

```text
without_evidence → fallback_answer
```

Esto reemplaza operativamente el criterio anterior de:

```text
"Chroma devolvió documentos"
```

por:

```text
"quedó al menos un documento después de validar relevancia"
```

sin modificar la implementación de `evidence_route`.

## Observabilidad

Durante ejecución real se registra una línea por documento:

```text
Relevance grading | doc=1 | source=Resolución 1401 de 2007 | article=6° | relevant=True | reason=...
```

y un resumen:

```text
Relevance grading summary | retrieved=5 | accepted=3 | rejected=2 | fallback=0
```

Esto permite inspeccionar:

* qué documentos recuperó originalmente Chroma;
* cuáles fueron aceptados;
* cuáles fueron rechazados;
* por qué se tomó cada decisión;
* cuáles fueron conservados exclusivamente por fallback.

La instrumentación es especialmente útil para detectar graders demasiado permisivos o demasiado restrictivos.

## Pruebas implementadas

La técnica cuenta con pruebas unitarias aisladas del RAG real.

Casos cubiertos:

1. conserva documentos marcados como relevantes;
2. elimina documentos marcados como irrelevantes;
3. conserva documentos cuando falla el grader;
4. maneja correctamente una entrada sin documentos.

Las pruebas usan dobles de prueba (`FakeLLM` y `FakeGrader`), por lo que no requieren:

* Chroma;
* Groq;
* modelo de embeddings;
* conexión a Internet;
* ejecución completa de LangGraph.

Comando:

```bash
python -m pytest agents/consulta_normativa/tests/test_retrieval_relevance_grading.py -v
```

Resultado observado durante implementación:

```text
3 passed
```

## Validación manual del flujo

La técnica también fue ejecutada dentro del RAG real mediante:

```bash
python -m agents.consulta_normativa.langchain_rag.main
```

Se utilizaron dos tipos de consultas.

### Consulta dentro del dominio

```text
¿Quién debe investigar los accidentes de trabajo?
```

El pipeline conservó evidencia normativa relacionada con la investigación de accidentes y permitió continuar hacia generación de respuesta.

### Consulta fuera del dominio

```text
¿Cuáles son los requisitos para renovar un pasaporte colombiano?
```

Aunque el retriever produjo candidatos, el grader rechazó la evidencia recuperada y el grafo terminó en el fallback:

```text
La evidencia recuperada es insuficiente para responder la pregunta.
```

Este caso permite comprobar la diferencia entre recuperar documentos por similitud y disponer realmente de evidencia relevante.

## Notas operativas

* Con `top_k = 5`, la implementación puede realizar hasta cinco llamadas adicionales al LLM por consulta, una por documento recuperado.
* El coste y latencia crecen aproximadamente con el número de documentos evaluados.
* La técnica no debe confundirse con reranking: no reordena documentos mediante scores, sino que decide cuáles continúan.
* Tampoco debe confundirse con Answerability: conservar documentos relevantes no implica que el conjunto sea suficiente para responder completamente la pregunta.
* El grader es un componente probabilístico y puede producir falsos positivos o falsos negativos.
* La política `fail-open` prioriza no perder evidencia normativa ante fallos técnicos del evaluador.

## Ejemplo de integración en LangGraph
state.py
```python
class RagGraphState(TypedDict, total=False):
    """State passed through the minimal LangGraph RAG flow."""

    question: str
    raw_results: dict[str, Any]
    documents: list[RetrievedDocument]
    retrieval_traces: list[dict[str, Any]]
    context: str
    references: list[str]
    messages: list[Any]
    prompt: str
    answer: str
    result: LangChainRagResult

    # Retrieval Relevance Grading
    relevance_grading_trace: dict[str, Any]

```
grap.py

```python
"""LangGraph RAG flow for normative consultation."""

from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.config import DEFAULT_TOP_K
from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult
from agents.consulta_normativa.langchain_rag.prompts import BASE_SYSTEM_INSTRUCTIONS, build_base_prompt, build_human_prompt
from agents.consulta_normativa.langchain_rag.query_understanding.rewrite_query import rewrite_query_node

#VALIDACION DE RELEVANCIA DE DOCUMENTOS RECUPERADOS
from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (retrieval_relevance_grading_node)

Retriever = Callable[[str, int], dict[str, Any]]


def build_langgraph_rag(llm: Any, retriever: Retriever, top_k: int = DEFAULT_TOP_K) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    

    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)

    #VALIDACION DE RELEVANCIA DE DOCUMENTOS RECUPERADOS
    workflow.add_node("grade_retrieval_relevance",retrieval_relevance_grading_node(llm))

    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    workflow.set_entry_point("retrieve")
    
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")
    
    #VALIDACION DE RELEVANCIA DE DOCUMENTOS RECUPERADOS
    workflow.add_edge("record_retrieval_trace","grade_retrieval_relevance")
    workflow.add_conditional_edges(
        "grade_retrieval_relevance",
        evidence_route,
        {
            "with_evidence": "format_context",
            "without_evidence": "fallback_answer",
        },
    )



    workflow.add_edge("fallback_answer", "format_result")
    workflow.add_edge("format_context", "build_messages")
    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("format_result", END)
    return workflow.compile()


def answer_with_langgraph(question: str, graph: Any) -> LangChainRagResult:
    """Run a compiled LangGraph-like object and return its RAG result."""

    state = graph.invoke({"question": question})
    result = state.get("result") if isinstance(state, dict) else None
    if not isinstance(result, LangChainRagResult):
        raise ValueError("LangGraph execution did not produce a LangChainRagResult.")
    return result


def retrieve_node(retriever: Retriever, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that retrieves raw Chroma-like results."""

    def run(state: RagGraphState) -> RagGraphState:
        retrieval_query = state.get("retrieval_query") or state["question"]
        return {"raw_results": retriever(retrieval_query, top_k)}

    return run


def normalize_documents_node(state: RagGraphState) -> RagGraphState:
    """Normalize raw retrieval output into retrieved documents."""

    return {"documents": recovered_documents(state.get("raw_results", {}))}


def fallback_answer_node(state: RagGraphState) -> RagGraphState:
    """Return the deterministic manual fallback without invoking the LLM."""
    context = "No se recuperó contexto."

    return {
        "context": context,
        "references": [],
        "prompt": build_base_prompt(state["question"], context),
        "answer": fallback_answer(context, []),
    }


def format_context_node(state: RagGraphState) -> RagGraphState:
    """Build context and references from retrieved documents."""

    documents = state.get("documents", [])
    return {
        "context": build_context(documents),
        "references": build_references(documents),
    }


def build_messages_node(state: RagGraphState) -> RagGraphState:
    """Build LangChain chat messages equivalent to the manual prompt input."""

    try:
        # pyrefly: ignore [missing-import]
        from langchain_core.messages import HumanMessage, SystemMessage
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langchain is not installed: {error}") from error

    context = state["context"]
    return {
        "messages": [
            SystemMessage(content=BASE_SYSTEM_INSTRUCTIONS),
            HumanMessage(content=build_human_prompt(state["question"], context)),
        ],
        "prompt": build_base_prompt(state["question"], context),
    }


def generate_answer_node(llm: Any) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that invokes the LLM with LangChain messages."""

    def run(state: RagGraphState) -> RagGraphState:
        return {"answer": invoke_llm_text(llm, state["messages"])}

    return run


def fallback_answer(context: str, references: list[str]) -> str:
    """Replicate the manual deterministic fallback answer exactly."""

    if context == "No se recuperó contexto.":
        return "La evidencia recuperada es insuficiente para responder la pregunta."
    return "\n".join(["Borrador fundamentado solo en el contexto recuperado:", context, "Referencias:", *references])


def format_result_node(state: RagGraphState) -> RagGraphState:
    """Build the public result object from graph state."""

    return {
        "result": LangChainRagResult(
            answer=state["answer"],
            references=state.get("references", []),
            context=state["context"],
            prompt=state["prompt"],
        )
    }

```

Durante la evaluación aislada de esta técnica, otras técnicas experimentales de comprensión de consulta, recuperación o validación deben permanecer desactivadas para evitar atribuir sus efectos a Retrieval Relevance Grading.
