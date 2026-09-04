# ARES - Parent Document Retrieval

Resumen de la corrida de evaluación ARES ejecutada sobre el conjunto `parent_document_retrieval.tsv`.

## Resumen Ejecutivo

| Campo | Valor |
|---|---:|
| Modelo usado | `deepseek-v4-flash` |
| Conjunto de evaluación | `evaluation/results/ares_runs/retrieval/parent_document_retrieval.tsv` |
| Tamaño del conjunto | 80 ejemplos |
| Checkpoints | Ninguno |
| Etiquetas evaluadas | `Context_Relevance_Label`, `Answer_Faithfulness_Label`, `Answer_Relevance_Label` |
| Ejemplos anotados para PPI | 200 |

## Resultados por etiqueta

| Etiqueta | Predicción ARES | Intervalo de confianza | Performance real | Accuracy del juez LLM |
|---|---:|---:|---:|---:|
| Context_Relevance_Label | 0.9100 | [0.839, 0.981] | 1.0000 | 0.9000 |
| Answer_Faithfulness_Label | 1.1275 | [1.061, 1.194] | 1.0000 | 0.9630 |
| Answer_Relevance_Label | 0.9750 | [0.941, 1.009] | 1.0000 | 0.9750 |

## Observaciones de la corrida

| Tipo | Detalle | Impacto |
|---|---|---|
| Advertencia de etiquetas | ARES reportó etiquetas incorrectas `1` y `0`; recomienda usar `[[Yes]]` y `[[No]]` | Puede afectar la limpieza de la evaluación y conviene corregir el formato de etiquetas |
| PPI | Se registraron advertencias por media de slice vacío y grados de libertad insuficientes | Sugiere revisar el subconjunto anotado o la configuración de PPI |
| Cobertura | La ejecución completó 80/80 ejemplos y 1000/1000 trials | La corrida terminó de forma completa |

## Lectura rápida

| Etiqueta | Lectura |
|---|---|
| Context_Relevance_Label | Buen desempeño, pero es la métrica más baja de las tres |
| Answer_Faithfulness_Label | Mejor predicción promedio, aunque supera 1.0 |
| Answer_Relevance_Label | Resultado alto y el más cercano a 1.0 |

## Notas

- La `Ground Truth Performance` fue 1.0 en las tres etiquetas.
- El valor mayor a 1.0 en `Answer_Faithfulness_Label` conviene revisarlo, porque puede reflejar una escala o calibración particular del estimador.
- Si se reejecuta el experimento, conviene normalizar las etiquetas al formato esperado por ARES antes de correr la evaluación.
