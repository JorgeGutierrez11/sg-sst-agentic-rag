# Resumen ARES: R2 Hybrid Reranking

Se evaluó el archivo [r2_hybrid_reranking.tsv](../../ares_runs/retrieval/r2_hybrid_reranking.tsv) con el modelo `deepseek-v4-flash` sobre 80 ejemplos, usando 200 ejemplos anotados para PPI.

## Síntesis ejecutiva

| Indicador | Valor |
|---|---:|
| Modelo evaluador | `deepseek-v4-flash` |
| Archivo evaluado | `evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv` |
| Número de ejemplos | 80 |
| Ejemplos anotados para PPI | 200 |
| Promedio simple de ARES | 1.033 |
| Promedio simple de accuracy del juez LLM | 0.963 |

## Resultados por etiqueta

| Métrica | Predicción ARES | IC ARES | Ground Truth | Accuracy juez LLM | Ejemplos |
|---|---:|---:|---:|---:|---:|
| `Context_Relevance_Label` | 0.9400 | [0.877, 1.003] | 1.0 | 0.925 | 80 |
| `Answer_Faithfulness_Label` | 1.1700 | [1.104, 1.236] | 1.0 | 0.975 | 80 |
| `Answer_Relevance_Label` | 0.9875 | [0.963, 1.012] | 1.0 | 0.988 | 80 |

## Lectura rápida

| Dimensión | Lectura |
|---|---|
| Relevancia de contexto | Alta, aunque con ligera subestimación frente al valor de referencia. |
| Fidelidad de la respuesta | Es la métrica más alta del conjunto; el intervalo de confianza queda claramente por encima de 1.0. |
| Relevancia de la respuesta | Mantiene un nivel alto y estable, cercano al valor ideal. |
| Señal global | El reranking híbrido conserva buen desempeño general, con su mejor señal en fidelidad. |


## Salida de referencia

```text
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  2%|██▍                                                                                             | 2/80 [00:10<06:30,  5.01s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [15:04<00:00, 11.30s/it]
Evaluating:   0%|                                                                                           | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                              | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 39.99it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv
Checkpoint:None
ARES Prediction: [0.939999999999998]
ARES Confidence Interval: [[0.877, 1.003]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.925]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [14:52<00:00, 11.15s/it]
Evaluating:   0%|                                                                                           | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                              | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.85it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv
Checkpoint:None
ARES Prediction: [1.170000000000011]
ARES Confidence Interval: [[1.104, 1.236]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.975]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [07:41<00:00,  5.76s/it]
Evaluating:   0%|                                                                                           | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                              | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 38.86it/s]
--------------------------------------------------
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv
Checkpoint:None
ARES Prediction: [0.9875000000000071]
ARES Confidence Interval: [[0.963, 1.012]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.988]
Annotated Examples used for PPI: 200
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv', 'ARES_Prediction': 0.939999999999998, 'ARES_Confidence_Interval': [0.877, 1.003], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.925, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv', 'ARES_Prediction': 1.170000000000011, 'ARES_Confidence_Interval': [1.104, 1.236], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.975, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r2_hybrid_reranking.tsv', 'ARES_Prediction': 0.9875000000000071, 'ARES_Confidence_Interval': [0.963, 1.012], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.988, 'Annotated_Examples_used_for_PPI': 200}]
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ 
```
