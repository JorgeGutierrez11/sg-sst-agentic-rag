Sí. Con esta arquitectura, el plan anterior debe ajustarse bastante. El cambio principal es que **ya tienes resuelto el identificador estable y el corpus canónico**: `chunk_id` para child chunks e `id` para tablas. No necesitas reconstruir identidad desde Chroma.

## 1. Arquitectura objetivo

Mantendría estrictamente la separación actual:

```text
OFFLINE
────────────────────────────────────────

JSONL child chunks + table documents
          │
          ├───────────────┐
          ↓               ↓
  Dense indexing      Sparse indexing
      Chroma              BM25
          │               │
          ↓               ↓
data/processed/chroma   data/processed/bm25


ONLINE
────────────────────────────────────────

             retrieval_query
                   │
          ┌────────┴────────┐
          ↓                 ↓
       Chroma              BM25
       Dense              Sparse
          │                 │
          ↓                 ↓
    ranking dense     ranking sparse
          └────────┬────────┘
                   ↓
                  RRF
                   ↓
              final_top_k
                   ↓
          pipeline RAG actual
                   ↓
                  ARES
```

**No metería construcción de BM25 dentro del agente.** Igual que Chroma, el índice sparse debe existir antes de levantar el RAG.

BM25S permite indexar un corpus, asociarle registros estructurados y persistir/cargar posteriormente tanto índice como corpus. ([GitHub][1])

---

# 2. No modificaría la vectorización dense existente

Tu pipeline actual:

```text
pipeline/vectorization/
```

debe continuar siendo responsable de:

```text
artefactos vector-ready
→ embeddings
→ Chroma
```

No convertiría `pipeline/vectorization/` en:

```text
Chroma
+ BM25
+ Hybrid Retrieval
```

porque **BM25 no es vectorización**.

Crearía una capa offline paralela, por ejemplo:

```text
pipeline/
├── vectorization/
│   └── Chroma / dense
│
└── sparse_indexing/
    └── BM25
```

Con algo pequeño:

```text
pipeline/sparse_indexing/
├── main.py
├── ingest.py
└── bm25_store.py
```

No necesitas replicar toda la arquitectura de vectorización.

---

# 3. Fuente del índice BM25

Aquí cambia una recomendación importante respecto al plan anterior.

**No construiría BM25 leyendo Chroma.**

Ya tienes los artefactos originales:

```text
JSONL child chunks
JSONL table documents
```

Esos deben alimentar:

```text
Chroma
y
BM25
```

por separado.

Es decir:

```text
                   mismos artefactos
                         │
               ┌─────────┴─────────┐
               ↓                   ↓
       ChromaRecord            BM25 document
               │                   │
               ↓                   ↓
             dense               sparse
```

Esto evita convertir Chroma en una fuente de verdad que realmente no lo es.

---

# 4. Reutilizar exactamente los mismos IDs

Tu diseño actual ya tiene:

```text
Child:
id = chunk_id

Table:
id = id
```

Eso es justamente lo que necesita RRF.

El registro sparse debería conservar conceptualmente:

```python
{
    "id": "...",
    "text": "...",
    "metadata": {...},
}
```

BM25S permite precisamente asociar diccionarios arbitrarios al corpus y devolver esos registros después del retrieval. ([GitHub][1])

Así obtienes:

```text
Dense:
chunk_005
chunk_123
table_012

Sparse:
chunk_123
chunk_078
table_012
```

y RRF fusiona mediante:

```text
id
```

No mediante comparación de texto.

---

# 5. Problema crítico: sincronización Chroma ↔ BM25

Este es ahora el riesgo arquitectónico principal.

Actualmente Chroma usa:

```python
collection.upsert(...)
```

y ya sabes que:

> si desaparece un documento del JSONL, puede permanecer en Chroma.

Pero BM25 probablemente será reconstruido completamente desde el corpus actual.

Entonces podrías terminar con:

```text
Corpus actual:
330 documentos

BM25:
330 documentos

Chroma:
337 documentos
↑
7 registros obsoletos
```

Eso **contamina Hybrid Retrieval**.

Podrías recuperar:

```text
Dense → chunk_obsoleto_001
Sparse → nunca lo puede encontrar
```

y RRF estaría fusionando rankings construidos sobre universos documentales diferentes.

### Antes del experimento Hybrid

Yo haría obligatorio:

```text
1. eliminar Chroma actual
2. reconstruir Chroma limpio
3. construir BM25
4. verificar igualdad de IDs
```

Debe cumplirse:

```python
dense_ids == sparse_ids
```

al momento de construir los índices.

Este test es mucho más importante que cualquier optimización de BM25.

---

# 6. Añadir un manifiesto del corpus

Para evitar el problema anterior, añadiría una verificación pequeña.

No una infraestructura complicada.

Por ejemplo:

```text
data/processed/
├── chroma/
├── bm25/
└── retrieval_manifest.json
```

Con:

```json
{
  "document_count": 330,
  "corpus_hash": "...",
  "ids_hash": "..."
}
```

El objetivo no es que el agente dependa del manifiesto para responder.

Sirve para comprobar:

```text
Chroma
   │
   ├── misma versión del corpus
   │
BM25
```

Antes de ejecutar experimentos.

Esto evita resultados experimentales inválidos por índices desincronizados.

---

# 7. Índice BM25

Usaría **BM25S**.

Su paper presenta una implementación Python basada en matrices sparse y reporta mejoras importantes de velocidad respecto a implementaciones Python tradicionales. ([arXiv][2])

Además soporta explícitamente:

```python
retriever.index(...)
retriever.save(...)
BM25.load(...)
```

y persistencia del corpus asociado. ([GitHub][1])

### Construcción

Conceptualmente:

```text
child/table records
        ↓
extraer text
        ↓
tokenizar
        ↓
BM25.index()
        ↓
save()
```

Ubicación:

```text
data/processed/bm25/
```

---

# 8. Tokenización: empezar simple

No metería todavía:

```text
stemming español
lemmatization
stopwords custom SG-SST
sinónimos
ontologías
query expansion
```

Porque dejarías de evaluar simplemente Hybrid Retrieval.

Primera variante:

```text
normalización mínima
      ↓
tokenización
      ↓
BM25
```

Pero hay algo que debes cuidar especialmente:

```text
Resolución 0312
Decreto 1072
CIIU 6920
COPASST
SG-SST
2.2.4.6.12
```

Una normalización agresiva que destruya estas expresiones sería contraproducente.

El propósito de BM25 en vuestro sistema es precisamente mejorar recuperación de **coincidencias léxicas exactas y terminología normativa**.

---

# 9. Nuevo helper runtime sparse

Siguiendo tu arquitectura existente:

```text
agents/shared/chroma_retrieval.py
```

yo añadiría paralelamente:

```text
agents/shared/bm25_retrieval.py
```

Responsabilidad única:

```text
abrir índice BM25 existente
        ↓
recibir query + top_k
        ↓
devolver ranking sparse
```

No debe:

```text
❌ construir índice
❌ modificar corpus
❌ fusionar rankings
❌ generar contexto
❌ llamar al LLM
```

Así mantienes simetría:

```text
agents/shared/
├── chroma_retrieval.py
└── bm25_retrieval.py
```

---

# 10. Contrato común de candidatos

Aquí sí haría un pequeño ajuste.

Actualmente `formatting.py` ya conserva el ID de Chroma como metadata auxiliar.

Para Hybrid Retrieval te conviene que la identidad documental deje de ser accidental y sea parte explícita del candidato.

Algo conceptualmente como:

```text
RetrievedDocument
├── id
├── document
├── metadata
└── retrieval info
```

No necesitas meter obligatoriamente todos los scores dentro del mismo objeto si eso complica el modelo.

Podrías separar:

```text
RetrievedDocument
```

de:

```text
RankedCandidate
```

Pero **solo lo haría si tu modelo actual lo necesita**. No crearía otra clase por anticipación.

Lo imprescindible es poder acceder a:

```text
document_id
```

sin rebuscarlo en metadata.

---

# 11. Dense retriever

Tu helper actual ya ejecuta:

```text
query_texts=[retrieval_query]
n_results=top_k
include=[
    "documents",
    "metadatas",
    "distances"
]
```

Eso se mantiene.

Chroma devuelve IDs independientemente de los campos incluidos y permite obtener documents, metadata y distances asociados. ([GitHub][1])

Resultado conceptual:

```text
DenseRankingEntry
├── id
├── rank
├── distance
├── document
└── metadata
```

No necesitas cambiar el embedding:

```text
Qwen/Qwen3-Embedding-0.6B
```

porque ese es precisamente tu baseline dense.

---

# 12. Sparse retriever

El BM25 runtime devuelve:

```text
SparseRankingEntry
├── id
├── rank
├── bm25_score
├── document
└── metadata
```

BM25S retorna resultados y scores para cada query y permite asociar el corpus original con esos resultados. ([GitHub][1])

---

# 13. RRF

Aquí mantendría una implementación propia y pequeña.

La técnica original de Cormack, Clarke y Büttcher fusiona múltiples rankings utilizando la posición de cada documento, no sus scores originales. ([G. V. Cormack][3])

Fórmula:

[
RRF(d)=
\sum_{r \in Rankings}
\frac{1}{k + rank_r(d)}
]

Usaría inicialmente:

```text
rrf_k = 60
```

porque es el valor clásico empleado en el trabajo original. ([G. V. Cormack][3])

### Ejemplo

```text
Dense:
1 A
2 B
3 C

Sparse:
1 B
2 D
3 A
```

Resultado:

```text
A → contribución dense + sparse
B → contribución dense + sparse
C → solo dense
D → solo sparse
```

---

# 14. No utilizar scores para fusionar

Mantén:

```text
Chroma distance
```

y:

```text
BM25 score
```

solo como observabilidad.

No hagas:

```python
combined = dense_score + bm25_score
```

RRF precisamente evita necesitar calibrar scores provenientes de sistemas diferentes. ([G. V. Cormack][3])

---

# 15. LangGraph

Tu variante experimental debería quedar:

```text
                 retrieval_query
                       │
              ┌────────┴────────┐
              ↓                 ↓
       dense_retrieve      sparse_retrieve
              │                 │
              └────────┬────────┘
                       ↓
                    rrf_fuse
                       ↓
                 assess_evidence
                       ↓
                  format_context
                       ↓
                 build_messages
                       ↓
                 generate_answer
                       ↓
                  format_result
```

### Importante

No reutilices todavía:

```text
Multi-Query RRF
```

aunque ya tengas helpers RRF para esa técnica.

Puedes reutilizar **la función pura que calcula RRF** si su contrato es genérico.

Pero no reutilices un nodo diseñado específicamente alrededor de:

```text
query_variants
variant_results
fan-out Multi-Query
```

para Hybrid Retrieval.

La matemática RRF es común.

La orquestación no.

---

# 16. ¿Paralelo o secuencial?

Arquitectónicamente:

```text
dense ──┐
        ├→ RRF
sparse ─┘
```

es fan-out/fan-in.

Pero inicialmente **no necesitas ejecutar ambas ramas concurrentemente**.

Primera implementación:

```text
dense
↓
sparse
↓
RRF
```

con el mismo resultado lógico.

Cuando el experimento funcione correctamente puedes paralelizar:

```text
dense ──┐
        ├→ RRF
sparse ─┘
```

No mezclaría optimización de latencia con implementación funcional inicial.

---

# 17. Parámetros experimentales

Tu baseline actual entrega:

```text
top_k = 5
```

Mantendría:

```text
final_top_k = 5
```

para que la cantidad de contexto enviada al LLM sea constante.

Primera configuración razonable:

```text
dense_top_k = 10
sparse_top_k = 10

        ↓
       RRF

final_top_k = 5
```

Pero esos `10` son un hiperparámetro experimental.

Si quieres máxima limpieza inicialmente:

```text
dense_top_k = 5
sparse_top_k = 5
final_top_k = 5
```

y posteriormente calibras el candidate pool.

Lo fijo debe ser:

```text
final_top_k baseline = final_top_k hybrid
```

---

# 18. Flujo offline recomendado

Aquí integraría la preparación de índices de esta manera:

```text
vector-ready JSONL
        │
        ├──────────────────────┐
        │                      │
        ↓                      ↓
vectorization.main      sparse_indexing.main
        │                      │
        ↓                      ↓
      Chroma                  BM25
        │                      │
        └──────────┬───────────┘
                   ↓
             validation
                   ↓
            compare ID sets
                   ↓
            corpus manifest
```

No obligaría a que ambos se construyan mediante el mismo comando todavía.

Podrías tener:

```bash
python -m pipeline.vectorization.main --batch-size 8

python -m pipeline.sparse_indexing.main
```

y después:

```text
validate_retrieval_indices
```

---

# 19. Flujo runtime recomendado

```text
main.py
  ↓
abrir Chroma existente
  ↓
abrir BM25 existente
  ↓
construir Hybrid LangGraph
  ↓
query
```

Igual que con Chroma:

> **Si BM25 no existe, la variante Hybrid debe fallar.**

No debe:

```text
BM25 missing
↓
crear índice vacío
↓
continuar
```

Eso ocultaría un error operativo.

---

# 20. Tests

### Offline

**Corpus parity**

```text
IDs Chroma
==
IDs BM25
```

Este test es obligatorio.

---

### BM25

Consulta léxica conocida:

```text
Resolución 0312
```

Debe recuperar documentos que contengan esa referencia.

---

### RRF

Usar rankings artificiales:

```text
dense = A B C
sparse = B D A
```

y comprobar cálculo exacto.

---

### Deduplicación

Un documento presente en ambas ramas:

```text
chunk_123
```

debe aparecer una sola vez después de RRF.

---

### Metadata

El documento fusionado debe conservar:

```text
source
article
paragraph
table information
...
```

para que `format_context()` continúe funcionando sin cambios importantes.

---

### Regresión

Debe seguir funcionando:

```text
Dense baseline
```

sin exigir que exista BM25.

---

# 21. Riesgo que corregiría antes del experimento

Tu mayor problema actual no es BM25 ni RRF.

Es:

> **Chroma puede contener registros obsoletos por `upsert`.**

Antes de generar resultados experimentales:

```text
eliminar data/processed/chroma
        ↓
reindexar dense
        ↓
crear BM25 desde el mismo corpus
        ↓
comparar IDs
        ↓
ejecutar ARES
```

De lo contrario no puedes garantizar que las dos ramas estén recuperando sobre el mismo corpus.

---

# 22. Orden definitivo de implementación

1. **Rebuild limpio del corpus dense.**
   Eliminar registros históricos de Chroma.

2. **Definir corpus canónico para ambos índices.**
   Mismos child chunks y table documents.

3. **Preservar IDs canónicos.**
   `chunk_id` e `id`.

4. **Crear `pipeline/sparse_indexing/`.**

5. **Construir y persistir BM25S.**

6. **Guardar/verificar manifiesto del corpus.**

7. **Crear `agents/shared/bm25_retrieval.py`.**

8. **Implementar retrieval sparse query-only.**

9. **Normalizar resultados dense/sparse alrededor del mismo `id`.**

10. **Implementar RRF como función pura e independiente.**

11. **Implementar variante Hybrid LangGraph.**

12. **Mantener `final_top_k=5`.**

13. **Tests unitarios de BM25 y RRF.**

14. **Test crítico de igualdad de IDs entre índices.**

15. **Tests de integración.**

16. **Ejecutar baseline Dense con ARES.**

17. **Ejecutar Dense + BM25 + RRF con ARES.**

18. **Comparar resultados.**

## Fuentes

Para **RRF**, usaría el paper original de Cormack, Clarke y Büttcher, que define la técnica de fusión de rankings. ([G. V. Cormack][3])
[Reciprocal Rank Fusion — paper original](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf?utm_source=chatgpt.com)

Para **BM25S**, tienes tanto el paper como el repositorio/documentación donde están descritos indexación, corpus estructurado, persistencia y carga del índice. ([arXiv][2])
[BM25S — paper](https://arxiv.org/abs/2407.03618?utm_source=chatgpt.com)
[BM25S — repositorio oficial](https://github.com/xhluca/bm25s?utm_source=chatgpt.com)

El siguiente paso útil es definir **el contrato exacto de `BM25Result`/candidato fusionable y la estructura de `pipeline/sparse_indexing/`** antes de tocar LangGraph; si esa interfaz queda mal, RRF terminará acoplado a detalles de Chroma o BM25.

[1]: https://github.com/xhluca/bm25s?utm_source=chatgpt.com "GitHub - xhluca/bm25s: Fast BM25 search in Python, powered by Numpy and Numba · GitHub"
[2]: https://arxiv.org/abs/2407.03618?utm_source=chatgpt.com "BM25S: Orders of magnitude faster lexical search via eager sparse scoring"
[3]: https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf?utm_source=chatgpt.com "sigir_main.dvi"
