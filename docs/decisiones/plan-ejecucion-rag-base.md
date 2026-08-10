# Plan de implementación: ejecución del RAG base

Este plan define la capa ejecutable para consultar el RAG base de SG-SST desde terminal. La implementación debe conectar la colección ChromaDB ya indexada con el flujo `answer_question` del agente de consulta normativa.

## Objetivo

Crear un punto de entrada operativo que permita ejecutar una pregunta contra el RAG base.

El flujo esperado es:

```txt
pregunta del usuario
  → abrir colección ChromaDB
  → crear retriever
  → construir contexto recuperado
  → construir prompt base
  → generar respuesta o fallback
  → imprimir respuesta y referencias
```

## Alcance

### Incluido

- CLI para ejecutar una consulta del RAG base.
- Apertura de la colección ChromaDB persistente.
- Uso de `chroma_retriever(collection)` como recuperador.
- Uso de `answer_question(...)` como flujo RAG principal.
- Generador LLM por defecto usando Groq vía `langchain_groq.ChatGroq`.
- Un único parámetro posicional para la pregunta.
- Salida legible con respuesta y referencias.
- Fallback determinístico solo si no se puede construir el generador LLM.

### Fuera de alcance

- Crear una API REST.
- Crear interfaz web.
- Memoria conversacional.
- Expansión hacia parent chunks.
- Reranking o búsqueda híbrida.
- Validación avanzada de respuestas.
- Selección o comparación de técnicas candidatas.

## Archivo propuesto

```txt
agents/consulta_normativa/main.py
```

## Comando esperado

```bash
python -m agents.consulta_normativa.main
```

## Argumentos CLI

| Argumento | Requerido | Valor por defecto | Propósito |
|---|---:|---|---|
| `question` | Sí | — | Pregunta normativa del usuario. |

El comando no debe exponer parámetros opcionales en esta etapa. Debe usar los valores por defecto del sistema:

| Configuración interna | Valor |
|---|---|
| Ruta ChromaDB | `data/processed/chroma` |
| Colección | `sg_sst_base_rag` |
| `top_k` | `5` |
| LLM | `openai/gpt-oss-120b` vía Groq |
| Temperatura | `0` |

## Generador LLM

La ejecución del RAG base debe construir internamente un generador compatible con el contrato `Generator = Callable[[str], str]`.

Implementación esperada:

```python
from langchain_groq import ChatGroq


def build_default_generator() -> Generator:
    """Return the default Groq-backed generator for the base RAG."""

    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
    )

    def generate(prompt: str) -> str:
        response = llm.invoke(prompt)
        return str(response.content)

    return generate
```

Requisito operativo:

```txt
GROQ_API_KEY
```

La clave debe leerse desde el entorno. No se debe guardar en archivos del proyecto ni imprimir en logs.

## Flujo de implementación

1. Crear parser CLI con subcomando `ask`.
2. Usar la ruta ChromaDB por defecto.
3. Abrir la colección por defecto con `open_collection`.
4. Crear retriever con `chroma_retriever(collection)`.
5. Construir generador por defecto con `build_default_generator()`.
6. Ejecutar `answer_question(question, retriever, generator=generator, top_k=5)`.
6. Imprimir `result.answer`.
7. Imprimir `result.references` como lista de fuentes usadas.

## Manejo de errores

- Si ChromaDB no está instalado, mostrar error controlado y retornar código `2`.
- Si `langchain_groq` no está instalado o `GROQ_API_KEY` no está configurada, mostrar error controlado y retornar código `2`.
- Si la colección no existe o no tiene documentos, mostrar que la evidencia recuperada es insuficiente.

## Salida esperada

Formato base:

```txt
Answer:
<respuesta>

References:
- <fuente 1>
- <fuente 2>
```

Si no hay evidencia:

```txt
Answer:
Recovered evidence is insufficient to answer the question.

References:
```

## Criterios de aceptación

- [ ] El comando `ask` se ejecuta desde la raíz del proyecto.
- [ ] El comando abre la colección ChromaDB persistente.
- [ ] El comando recupera `5` documentos por defecto.
- [ ] El comando construye el LLM por defecto con `ChatGroq(model="openai/gpt-oss-120b", temperature=0)`.
- [ ] El comando usa `answer_question` como flujo RAG único.
- [ ] La salida muestra respuesta y referencias.
- [ ] La clave `GROQ_API_KEY` se lee solo desde variables de entorno.
- [ ] Los errores operativos se reportan sin traceback.

## Resultado esperado

Al finalizar, el RAG base debe poder consultarse desde terminal usando la colección ChromaDB ya generada por `pipeline.vectorization.main ingest`.
