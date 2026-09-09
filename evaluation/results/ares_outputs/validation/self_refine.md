# Resumen ARES: Self Refine

Se evaluó el archivo [self_refine.tsv](../../ares_runs/validation/self_refine.tsv) con el modelo `deepseek-v4-flash` sobre 80 ejemplos, usando 200 ejemplos anotados para PPI.

## Síntesis ejecutiva

| Indicador | Valor |
|---|---:|
| Modelo evaluador | `deepseek-v4-flash` |
| Archivo evaluado | `evaluation/results/ares_runs/validation/self_refine.tsv` |
| Número de ejemplos | 80 |
| Ejemplos anotados para PPI | 200 |
| Promedio simple de ARES | 0.963 |
| Promedio simple de accuracy del juez LLM | 0.904 |

## Resultados por etiqueta

| Métrica | Predicción ARES | IC ARES | Ground Truth | Accuracy juez LLM | Ejemplos |
|---|---:|---:|---:|---:|---:|
| `Context_Relevance_Label` | 0.8100 | [0.715, 0.905] | 1.0 | 0.800 | 80 |
| `Answer_Faithfulness_Label` | 1.1100 | [1.040, 1.180] | 1.0 | 0.950 | 80 |
| `Answer_Relevance_Label` | 0.9675 | [0.925, 1.010] | 1.0 | 0.963 | 80 |

## Lectura rápida

| Dimensión | Lectura |
|---|---|
| Relevancia de contexto | La dimensión más débil del conjunto; muestra una mayor dificultad para decidir si el contexto es suficiente. |
| Fidelidad de la respuesta | La más sólida del experimento, con buen desempeño y alta precisión del juez. |
| Relevancia de la respuesta | Muy buena, cercana al ideal y con robustez del juez LLM. |
| Señal global | El enfoque presenta un desempeño razonable, pero la calidad del contexto sigue siendo el mayor cuello de botella. |


## Salida de referencia

```text
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  2%|██▍                                                                                             | 2/80 [00:06<04:30,  3.46s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [14:13<00:00, 10.66s/it]
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
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.36it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv
Checkpoint:None
ARES Prediction: [0.8099999999999983]
ARES Confidence Interval: [[0.715, 0.905]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.8]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [08:53<00:00,  6.66s/it]
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
Trials: 100%|███████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.89it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv
Checkpoint:None
ARES Prediction: [1.1100000000000048]
ARES Confidence Interval: [[1.04, 1.18]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.95]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                        | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [09:20<00:00,  7.00s/it]
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
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv
Checkpoint:None
ARES Prediction: [0.9674999999999883]
ARES Confidence Interval: [[0.925, 1.01]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.963]
Annotated Examples used for PPI: 200
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv', 'ARES_Prediction': 0.8099999999999983, 'ARES_Confidence_Interval': [0.715, 0.905], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.8, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv', 'ARES_Prediction': 1.1100000000000048, 'ARES_Confidence_Interval': [1.04, 1.18], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.95, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/ares_runs/validation/self_refine.tsv', 'ARES_Prediction': 0.9674999999999883, 'ARES_Confidence_Interval': [0.925, 1.01], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.963, 'Annotated_Examples_used_for_PPI': 200}]
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ 
```
