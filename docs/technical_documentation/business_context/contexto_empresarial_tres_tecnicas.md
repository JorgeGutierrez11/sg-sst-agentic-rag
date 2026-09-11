# Técnicas candidatas para construcción de contexto empresarial

## Propósito de la dimensión

La dimensión de **contexto empresarial** tiene como objetivo conservar información relevante sobre la empresa y sobre las interacciones previas del usuario para que otras etapas del agente puedan utilizarla posteriormente.

Esta dimensión **no modifica la consulta, no recupera normativa y no genera la respuesta final**. Su responsabilidad termina al construir un contexto reutilizable por técnicas posteriores, como Query Rewriting, Retrieval o generación.

El contexto empresarial puede contener dos tipos principales de información:

- **Perfil empresarial:** información relativamente estable de la organización, como actividad económica, código CIIU, número de trabajadores, clase de riesgo y otros datos relevantes.
- **Memoria histórica:** hechos, eventos, preguntas y respuestas provenientes de interacciones anteriores.

Ejemplo:

```text
Perfil empresarial
- Actividad económica: mantenimiento y reparación de motocicletas
- Número de trabajadores: 8
- Clase de riesgo: I

Historial relevante
- El usuario informó anteriormente que un trabajador sufrió una fractura
  mientras realizaba actividades laborales.
- Posteriormente consultó sobre la investigación del accidente.
```

Para gestionar la parte histórica del contexto se consideran tres técnicas candidatas.

---

## 1. Full Conversation Memory

### Definición

**Full Conversation Memory** consiste en conservar el historial completo de mensajes de una conversación y hacerlo disponible en las siguientes interacciones del mismo hilo.

En LangGraph este comportamiento corresponde a la **short-term memory** o memoria de corto plazo asociada a un `thread`. El estado del grafo, incluido el historial de mensajes, puede persistirse mediante un `checkpointer`.

### Funcionamiento

```text
Mensaje del usuario
        ↓
Se agrega al historial
        ↓
Ejecución del agente
        ↓
Respuesta del agente
        ↓
Se conserva el estado del thread
        ↓
Siguiente interacción
        ↓
Se recupera el historial completo
```

Ejemplo de historial almacenado:

```text
Usuario: Tengo una empresa de mantenimiento de motocicletas.
Agente: ...

Usuario: Tenemos 8 trabajadores.
Agente: ...

Usuario: Somos riesgo I.
Agente: ...

Usuario: Un trabajador se fracturó el brazo mientras trabajaba.
Agente: ...
```

Si posteriormente el usuario pregunta:

```text
¿Qué debo hacer con ese accidente?
```

el agente puede disponer de las interacciones anteriores para interpretar a qué accidente se refiere.

### Aplicación al contexto empresarial

El contexto entregado a las siguientes etapas podría construirse como:

```text
BUSINESS_CONTEXT

Perfil empresarial:
- actividad: mantenimiento y reparación de motocicletas
- trabajadores: 8
- riesgo: I

Historial conversacional:
- [mensaje 1]
- [respuesta 1]
- [mensaje 2]
- [respuesta 2]
...
```

### Ventajas

- Preserva literalmente las preguntas y respuestas anteriores.
- No requiere resumir ni seleccionar recuerdos.
- Reduce el riesgo de perder detalles por compresión.
- Es sencilla de implementar mediante persistencia del estado en LangGraph.

### Limitaciones

- El historial crece con cada interacción.
- Puede superar la ventana de contexto del LLM.
- Incrementa el número de tokens enviados al modelo.
- Puede aumentar latencia y costo.
- Información antigua o irrelevante puede distraer al modelo.

Por estas razones resulta adecuada como **baseline**, pero puede ser poco eficiente para conversaciones extensas.

### Implementación en LangGraph

LangGraph permite persistir la memoria de corto plazo mediante un `checkpointer`.

Conceptualmente:

```python
checkpointer = ...

graph = builder.compile(
    checkpointer=checkpointer
)
```

Cada conversación se identifica mediante un `thread_id`, permitiendo recuperar posteriormente el estado y sus mensajes.

### Fuentes

- LangChain. **Memory overview**.  
  https://docs.langchain.com/oss/python/concepts/memory

- LangChain. **Short-term memory**.  
  https://docs.langchain.com/oss/python/langchain/short-term-memory

- LangChain. **Persistence**.  
  https://docs.langchain.com/oss/python/langgraph/persistence

---

## 2. Summarization-Based Conversational Memory

### Definición

La **Summarization-Based Conversational Memory** conserva el contexto de conversaciones extensas reemplazando mensajes antiguos por un resumen acumulativo.

LangGraph documenta esta estrategia como **Summarize Messages** dentro de los mecanismos para gestionar memoria conversacional.

En vez de enviar siempre el historial completo, el agente mantiene normalmente:

```text
perfil empresarial
+
resumen de conversaciones anteriores
+
mensajes recientes
```

### Funcionamiento

```text
Historial conversacional
        ↓
¿Supera el límite definido?
        │
       Sí
        ↓
LLM de resumen
        ↓
Actualiza resumen acumulativo
        ↓
Elimina o excluye mensajes antiguos
        ↓
Resumen + mensajes recientes
```

Ejemplo.

Historial original:

```text
Usuario: Tenemos ocho trabajadores.
Usuario: La empresa está clasificada como riesgo I.
Usuario: Un trabajador sufrió una fractura del brazo mientras reparaba
         una motocicleta en el taller.
Usuario: ¿Debemos investigar ese accidente?
```

Resumen almacenado:

```text
La empresa tiene ocho trabajadores y está clasificada como riesgo I.
El usuario informó sobre un trabajador que sufrió una fractura mientras
realizaba labores en el taller y posteriormente consultó sobre la
investigación del accidente.
```

Las siguientes interacciones reciben el resumen en lugar de todo el historial antiguo.

### Aplicación al contexto empresarial

```text
BUSINESS_CONTEXT

Perfil empresarial:
- actividad: mantenimiento y reparación de motocicletas
- trabajadores: 8
- riesgo: I

Resumen histórico:
La empresa reportó anteriormente un accidente en el que un trabajador
sufrió una fractura durante actividades laborales. El usuario ya realizó
consultas relacionadas con la investigación del accidente.

Mensajes recientes:
- ...
```

### Ventajas

- Reduce el volumen de tokens utilizados.
- Permite mantener conversaciones de mayor duración.
- Mantiene una representación general de hechos tratados anteriormente.
- Evita enviar todo el historial al modelo en cada interacción.

### Limitaciones

La principal debilidad es que el resumen constituye una **compresión con pérdida**.

Por ejemplo, el mensaje original:

```text
El trabajador sufrió una fractura del brazo izquierdo el 14 de agosto
mientras realizaba mantenimiento a una motocicleta dentro del taller.
```

podría convertirse en:

```text
Anteriormente ocurrió un accidente laboral.
```

En ese proceso pueden perderse datos relevantes como:

- fecha;
- tipo de lesión;
- actividad ejecutada;
- lugar del accidente;
- personas involucradas.

En un dominio normativo como SG-SST esta pérdida puede ser importante, porque detalles aparentemente menores pueden cambiar la interpretación de una consulta posterior.

### Implementación en LangGraph

LangGraph permite agregar una propiedad de estado destinada al resumen:

```text
State
├── messages
└── summary
```

Cuando el historial alcanza determinado tamaño, un nodo de resumen utiliza:

```text
resumen anterior
+
mensajes nuevos
```

para producir un nuevo resumen acumulativo.

Posteriormente se conserva:

```text
nuevo resumen
+
mensajes recientes
```

### Fuentes

- LangChain. **Memory — Manage short-term memory / Summarize messages**.  
  https://docs.langchain.com/oss/python/langgraph/add-memory

- LangChain. **Short-term memory — Common patterns**.  
  https://docs.langchain.com/oss/python/langchain/short-term-memory

- LangChain. **Memory overview**.  
  https://docs.langchain.com/oss/python/concepts/memory

---

## 3. Retrieval-Based Long-Term Memory

### Definición

**Retrieval-Based Long-Term Memory** almacena información proveniente de interacciones anteriores como recuerdos independientes y, ante una nueva consulta, recupera únicamente aquellos que resultan relevantes.

A diferencia de Full Conversation Memory:

```text
no recupera todo el historial
```

y a diferencia de Summarization-Based Memory:

```text
no depende de un único resumen global
```

El sistema mantiene una colección persistente de recuerdos y realiza una búsqueda sobre ella.

LangGraph permite implementar este comportamiento mediante **long-term memory**, `Store` y búsqueda semántica.

### Funcionamiento

Durante las conversaciones se generan recuerdos:

```text
memory_001
type: business_fact
content: La empresa tiene 8 trabajadores.

memory_002
type: business_fact
content: La empresa está clasificada como riesgo I.

memory_003
type: incident
content: Un trabajador sufrió una fractura mientras realizaba
         actividades laborales.

memory_004
type: previous_query
content: El usuario consultó sobre la investigación del accidente.
```

Ante una nueva consulta:

```text
¿Qué debo hacer ahora con el accidente?
```

se ejecuta una recuperación:

```text
Pregunta actual
      ↓
Búsqueda sobre memoria
      ↓
Recuerdos relevantes
      ↓
memory_003
memory_004
      ↓
Construcción del contexto
```

Por tanto, el agente puede disponer de información histórica relevante sin incluir miles de mensajes anteriores.

### Aplicación al contexto empresarial

Una posible organización sería:

```text
namespace:
(company_id, "business_memory")
```

con recuerdos como:

```json
{
  "type": "incident",
  "content": "Un trabajador sufrió una fractura durante una actividad laboral."
}
```

o:

```json
{
  "type": "business_fact",
  "content": "La empresa tiene ocho trabajadores."
}
```

El contexto final podría construirse con:

```text
BUSINESS_CONTEXT

Perfil empresarial:
- actividad: mantenimiento y reparación de motocicletas
- trabajadores: 8
- riesgo: I

Memorias recuperadas:
1. Un trabajador sufrió anteriormente una fractura durante actividades laborales.
2. El usuario consultó posteriormente sobre la investigación del accidente.
```

### Recuperación semántica

LangGraph `Store` permite buscar recuerdos mediante similitud semántica cuando el almacenamiento está configurado con embeddings.

Conceptualmente:

```python
memories = store.search(
    namespace,
    query=current_question,
    limit=3
)
```

Esto permite que expresiones diferentes puedan recuperar un mismo hecho.

Por ejemplo:

```text
Memoria:
"Un trabajador sufrió una fractura mientras trabajaba."

Pregunta:
"¿Qué hago con la lesión que ocurrió en el taller?"
```

No es necesario que ambas cadenas contengan exactamente las mismas palabras para que exista similitud semántica.

### Respaldo académico

Esta estrategia no se limita a LangGraph.

**MemoryBank** propone un mecanismo de memoria de largo plazo para LLM que almacena información proveniente de interacciones anteriores y permite recuperar recuerdos relevantes posteriormente.

**Mem0** propone una arquitectura de memoria que extrae, consolida y recupera dinámicamente información relevante de conversaciones prolongadas. El trabajo compara el enfoque contra diferentes baselines, incluyendo uso del contexto conversacional completo y métodos basados en recuperación.

Estos trabajos respaldan la idea de separar el historial bruto del conjunto de recuerdos persistentes que se recuperan según la necesidad de cada consulta.

### Ventajas

- Escala mejor que enviar todo el historial.
- Permite compartir memoria entre diferentes sesiones.
- Recupera únicamente información relacionada con la consulta actual.
- Puede almacenar hechos empresariales, eventos y conversaciones previas como unidades independientes.
- Reduce el contexto innecesario enviado al LLM.

### Limitaciones

Introduce una nueva fuente de error: **la recuperación de memoria**.

Puede ocurrir:

```text
el recuerdo existe
        ↓
pero
        ↓
el sistema no lo recupera
```

Por ejemplo, si el sistema conserva:

```text
Un trabajador sufrió una fractura durante actividades laborales.
```

pero esa memoria no aparece entre los resultados recuperados para:

```text
¿Qué debo hacer con lo que le ocurrió al trabajador?
```

la siguiente etapa del agente no tendrá acceso al dato aunque este sí exista en la memoria.

Por ello deben evaluarse aspectos como:

- estrategia de extracción de recuerdos;
- granularidad de cada memoria;
- embeddings;
- número de recuerdos recuperados;
- filtros;
- actualización o eliminación de memorias;
- contradicciones entre recuerdos antiguos y nuevos.

### Implementación en LangGraph

LangGraph diferencia:

- `checkpointer`: persistencia asociada a un hilo;
- `Store`: memoria de largo plazo compartida entre hilos.

Una estructura posible sería:

```text
Store
└── company_id
    └── business_memory
        ├── memory_001
        ├── memory_002
        ├── memory_003
        └── ...
```

Con búsqueda:

```text
pregunta actual
      ↓
store.search(...)
      ↓
top-k recuerdos
      ↓
business_context
```

### Fuentes

- LangChain. **Memory overview — Long-term memory, Profile y Collection**.  
  https://docs.langchain.com/oss/python/concepts/memory

- LangChain. **Long-term memory**.  
  https://docs.langchain.com/oss/python/langchain/long-term-memory

- LangChain. **Persistence — Memory Store y Semantic Search**.  
  https://docs.langchain.com/oss/python/langgraph/persistence

- Zhong, W., Guo, L., Gao, Q., Ye, H., & Wang, Y. (2024).  
  **MemoryBank: Enhancing Large Language Models with Long-Term Memory.**  
  Proceedings of the AAAI Conference on Artificial Intelligence, 38(17), 19724–19731.  
  https://doi.org/10.1609/aaai.v38i17.29946

- Chhikara, P., Khant, D., Aryan, S., Singh, T., & Yadav, D. (2025).  
  **Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory.**  
  arXiv:2504.19413.  
  https://arxiv.org/abs/2504.19413

---

## Comparación de las técnicas candidatas

| Técnica | Estrategia | Persistencia entre sesiones | Consumo de contexto | Riesgo principal |
|---|---|---:|---:|---|
| Full Conversation Memory | Conserva el historial completo | Depende de la persistencia configurada | Alto y creciente | Contexto excesivo |
| Summarization-Based Conversational Memory | Resume historial antiguo y conserva mensajes recientes | Puede persistirse | Medio | Pérdida de información durante el resumen |
| Retrieval-Based Long-Term Memory | Almacena recuerdos independientes y recupera los relevantes | Sí | Bajo/variable | Fallos en recuperación de recuerdos |

---

## Relación con el perfil empresarial

El **perfil empresarial no debe confundirse con una técnica completa de gestión de memoria histórica**.

LangGraph describe un `Profile` como un documento, normalmente estructurado en JSON, que se actualiza progresivamente para representar información específica sobre una persona, organización u otra entidad.

Para SG-SST podría utilizarse:

```json
{
  "economic_activity": "mantenimiento y reparación de motocicletas",
  "ciiu_code": "4542",
  "worker_count": 8,
  "risk_class": "I"
}
```

El perfil permite conservar datos relativamente estables, pero por sí solo no representa adecuadamente:

- accidentes informados anteriormente;
- situaciones temporales;
- preguntas anteriores;
- respuestas anteriores;
- hechos ocurridos durante la interacción.

Por esta razón puede mantenerse como una estructura común a los experimentos y comparar las tres técnicas sobre la forma de incorporar la **memoria histórica**.

---

## Ubicación dentro del agente

La dimensión debe limitarse a construir contexto:

```text
Mensaje actual
      ↓
┌───────────────────────────────┐
│ Construcción de contexto      │
│ empresarial                   │
│                               │
│ Perfil empresarial            │
│          +                    │
│ Memoria histórica             │
└───────────────┬───────────────┘
                ↓
        BUSINESS_CONTEXT
                ↓
      Siguiente dimensión
                ↓
 Query Rewriting / Retrieval / ...
```

No debería realizar dentro de esta dimensión:

- Query Rewriting;
- expansión de consultas;
- recuperación de normativa;
- reranking;
- generación de la respuesta final.

Estas etapas pueden **consumir** `business_context`, pero pertenecen a otras dimensiones del agente.

---

## Técnicas seleccionadas para evaluación

Las tres técnicas candidatas de construcción de contexto histórico son:

1. **Full Conversation Memory**
2. **Summarization-Based Conversational Memory**
3. **Retrieval-Based Long-Term Memory**

El perfil empresarial puede mantenerse como componente común, mientras que el experimento modifica la estrategia utilizada para incorporar información histórica. Esto permite que las tres alternativas sean comparables bajo una misma responsabilidad arquitectónica.
