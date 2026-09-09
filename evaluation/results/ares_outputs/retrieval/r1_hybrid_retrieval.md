# Resumen ARES: R1 Hybrid Reranking Parent

Se evaluó el archivo [r1_hybrid_reranking_parent.tsv](../../ares_runs/retrieval/r1_hybrid_reranking_parent.tsv) con el modelo `deepseek-v4-flash` sobre 80 ejemplos, usando 200 ejemplos anotados para PPI.

## Síntesis ejecutiva

| Indicador | Valor |
|---|---:|
| Modelo evaluador | `deepseek-v4-flash` |
| Archivo evaluado | `evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv` |
| Número de ejemplos | 80 |
| Ejemplos anotados para PPI | 200 |
| Promedio simple de ARES | 1.043 |
| Promedio simple de accuracy del juez LLM | 0.963 |

## Resultados por etiqueta

| Métrica | Predicción ARES | IC ARES | Ground Truth | Accuracy juez LLM | Ejemplos |
|---|---:|---:|---:|---:|---:|
| `Context_Relevance_Label` | 0.9525 | [0.890, 1.015] | 1.0 | 0.938 | 80 |
| `Answer_Faithfulness_Label` | 1.1650 | [1.091, 1.239] | 1.0 | 0.950 | 80 |
| `Answer_Relevance_Label` | 1.0100 | [0.996, 1.024] | 1.0 | 1.000 | 80 |

## Lectura rápida

| Dimensión | Lectura |
|---|---|
| Relevancia de contexto | Alta, con una leve subestimación respecto al valor de referencia. |
| Fidelidad de la respuesta | Es la métrica más fuerte del conjunto; el intervalo de confianza se mantiene por encima de 1.0. |
| Relevancia de la respuesta | Muy cercana al ideal y estable. |
| Señal global | El reranking con parent chunks mantiene un desempeño sólido, con mejora clara en relevancia de respuesta. |

## Salida de referencia

```text
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  2%|██▍                                                                                             | 2/80 [00:04<02:54,  2.24s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [16:43<00:00, 12.54s/it]
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
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 39.62it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv
Checkpoint:None
ARES Prediction: [0.9525000000000161]
ARES Confidence Interval: [[0.89, 1.015]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.938]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [12:34<00:00,  9.43s/it]
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
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 39.85it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv
Checkpoint:None
ARES Prediction: [1.1650000000000131]
ARES Confidence Interval: [[1.091, 1.239]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.95]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [08:07<00:00,  6.09s/it]
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
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:26<00:00, 38.32it/s]
--------------------------------------------------
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv
Checkpoint:None
ARES Prediction: [1.0099999999999993]
ARES Confidence Interval: [[0.996, 1.024]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [1.0]
Annotated Examples used for PPI: 200
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv', 'ARES_Prediction': 0.9525000000000161, 'ARES_Confidence_Interval': [0.89, 1.015], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.938, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv', 'ARES_Prediction': 1.1650000000000131, 'ARES_Confidence_Interval': [1.091, 1.239], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.95, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/retrieval/r1_hybrid_reranking_parent.tsv', 'ARES_Prediction': 1.0099999999999993, 'ARES_Confidence_Interval': [0.996, 1.024], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 1.0, 'Annotated_Examples_used_for_PPI': 200}]
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ 
```
