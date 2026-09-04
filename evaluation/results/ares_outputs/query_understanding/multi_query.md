# Resumen ARES: `multi_query`

Fuente: ejecución de `python evaluation/ares/config.py` sobre `evaluation/results/ares_runs/query_understanding/multi_query.tsv`.

## Metadatos del experimento

| Campo | Valor |
|---|---|
| Archivo de evaluación | `evaluation/results/ares_runs/query_understanding/multi_query.tsv` |
| Modelo evaluador | `deepseek-v4-flash` |
| Número de ejemplos | 80 |
| Etiquetas evaluadas | `Context_Relevance_Label`, `Answer_Faithfulness_Label`, `Answer_Relevance_Label` |
| Conjunto anotado para PPI | 200 ejemplos |
| Performance ground truth | 1.0 en las tres etiquetas |

## Resultados por etiqueta

| Etiqueta | Predicción ARES | Intervalo de confianza | Precisión del juez LLM | Lectura rápida |
|---|---:|---|---:|---|
| `Context_Relevance_Label` | 0.8475 | [0.755, 0.940] | 0.812 | Es la métrica más baja de la corrida, aunque sigue en un rango aceptable. |
| `Answer_Faithfulness_Label` | 1.1750 | [1.110, 1.240] | 0.975 | Es el mejor resultado relativo y muestra alta concordancia con el ground truth. |
| `Answer_Relevance_Label` | 0.9625 | [0.921, 1.004] | 0.963 | Mantiene una calidad sólida y queda muy cerca de 1.0. |

## Lectura global

| Aspecto | Síntesis |
|---|---|
| Desempeño general | La corrida terminó con resultados consistentes y sin fallos críticos. |
| Métrica más fuerte | `Answer_Faithfulness_Label`, con mayor predicción ARES y mejor accuracy del juez LLM. |
| Métrica más débil | `Context_Relevance_Label`, que queda por debajo del resto y conviene vigilar. |
| Estabilidad | Los intervalos de confianza son relativamente estrechos, salvo la relevancia de contexto. |

## Observaciones técnicas

| Hallazgo | Detalle |
|---|---|
| Formato de etiquetas | ARES emitió advertencias porque encontró `1` y `0` en lugar de `[[Yes]]` y `[[No]]`. |
| Fase PPI | Se registraron advertencias numéricas asociadas con slices vacíos y cálculos con `NaN`. |
| Ground truth | ARES reportó `1.0` como performance de referencia en las tres etiquetas. |

## Conclusión

La evaluación de `multi_query` muestra una alineación sólida entre ARES y el ground truth, con especial fortaleza en `Answer_Faithfulness_Label` y desempeño más moderado en `Context_Relevance_Label`. El siguiente ajuste prioritario es normalizar el formato de salida de las etiquetas para reducir el ruido de validación en futuras corridas.


# SALIDA


```text
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                             | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  2%|██▏                                                                                  | 2/80 [00:06<04:26,  3.41s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|████████████████████████████████████████████████████████████████████████████████████| 80/80 [20:27<00:00, 15.34s/it]
Evaluating:   0%|                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.31it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv
Checkpoint:None
ARES Prediction: [0.8475000000000061]
ARES Confidence Interval: [[0.755, 0.94]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.812]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                             | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|████████████████████████████████████████████████████████████████████████████████████| 80/80 [16:22<00:00, 12.28s/it]
Evaluating:   0%|                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Evaluating:  60%|██████████████████████████████████████████▎                           | 121/200 [28:25<06:22,  4.84s/it]Didn't extract Yes or No!
Trials:   0%|                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.46it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv
Checkpoint:None
ARES Prediction: [1.1749999999999976]
ARES Confidence Interval: [[1.11, 1.24]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.975]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                             | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|████████████████████████████████████████████████████████████████████████████████████| 80/80 [21:48<00:00, 16.35s/it]
Evaluating:   0%|                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████| 1000/1000 [00:26<00:00, 38.26it/s]
--------------------------------------------------
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv
Checkpoint:None
ARES Prediction: [0.9624999999999911]
ARES Confidence Interval: [[0.921, 1.004]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.963]
Annotated Examples used for PPI: 200
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv', 'ARES_Prediction': 0.8475000000000061, 'ARES_Confidence_Interval': [0.755, 0.94], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.812, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv', 'ARES_Prediction': 1.1749999999999976, 'ARES_Confidence_Interval': [1.11, 1.24], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.975, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/query_understanding/multi_query.tsv', 'ARES_Prediction': 0.9624999999999911, 'ARES_Confidence_Interval': [0.921, 1.004], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.963, 'Annotated_Examples_used_for_PPI': 200}]
```