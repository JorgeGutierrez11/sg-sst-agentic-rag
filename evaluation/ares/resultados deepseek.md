# Resultados DeepSeek v2 - ARES

## Resumen de ejecución

| Campo | Valor |
| --- | --- |
| Modelo | `deepseek-v4-flash` |
| Archivo evaluado | `evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv` |
| Etiquetas evaluadas | `Context_Relevance_Label`, `Answer_Faithfulness_Label`, `Answer_Relevance_Label` |
| Número de ejemplos | 200 |
| Ejemplos anotados usados para PPI | 200 |
| Estado general | Ejecución completada sin error |

## Métricas comparadas

| Etiqueta | ARES | Intervalo de confianza | Ground truth | Diferencia ARES - GT | Accuracy del juez |
| --- | ---: | --- | ---: | ---: | ---: |
| Context_Relevance_Label | 0.9400 | [0.910, 0.970] | 0.930 | +0.010 | 0.935 |
| Answer_Faithfulness_Label | 0.9500 | [0.920, 0.980] | 0.940 | +0.010 | 0.955 |
| Answer_Relevance_Label | 0.9600 | [0.935, 0.985] | 0.960 | +0.000 | 1.000 |

## Lectura rápida

| Hallazgo | Interpretación |
| --- | --- |
| Context relevance alineada | La predicción de ARES quedó apenas por encima del ground truth, con una desviación mínima. |
| Answer faithfulness estable | El resultado también quedó cerca del valor esperado, aunque con menor confianza del juez que en context relevance. |
| Answer relevance exacta | La métrica coincidió con el ground truth y el juez mostró la mejor precisión posible. |
| Señal global consistente | Las tres métricas se movieron dentro de rangos razonables y sin desvíos fuertes. |


## Conclusión

| Síntesis | Resultado |
| --- | --- |
| Calidad general | Buena y más consistente que en la corrida anterior, con métricas cercanas al ground truth. |
| Mejor señal | `Answer_Relevance_Label`, por coincidencia exacta con el ground truth y accuracy perfecta del juez. |
| Riesgo principal | El formato de etiquetas sigue siendo el punto débil operativo. |
| Siguiente ajuste sugerido | Corregir la codificación de etiquetas antes de ejecutar una nueva evaluación. |


# Salida

```text
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                            | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  1%|▊                                                                                   | 2/200 [00:11<19:15,  5.84s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|██████████████████████████████████████████████████████████████████████████████████| 200/200 [30:03<00:00,  9.02s/it]
Evaluating:   0%|                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.64it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.9400000000000001]
ARES Confidence Interval: [[0.910, 0.970]]
Number of Examples in Evaluation Set: [200]
Ground Truth Performance: [0.93]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.935]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                            | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|██████████████████████████████████████████████████████████████████████████████████| 200/200 [21:43<00:00,  6.52s/it]
Evaluating:   0%|                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arr, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.58it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.9500000000000001]
ARES Confidence Interval: [[0.920, 0.980]]
Number of Examples in Evaluation Set: [200]
Ground Truth Performance: [0.94]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.955]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                            | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|██████████████████████████████████████████████████████████████████████████████████| 200/200 [09:19<00:00,  2.80s/it]
Evaluating:   0%|                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arr, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 39.01it/s]
--------------------------------------------------
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.96]
ARES Confidence Interval: [[0.935, 0.985]]
Number of Examples in Evaluation Set: [200]
Ground Truth Performance: [0.96]
ARES LLM Judge Accuracy on Ground Truth Labels: [1.0]
Annotated Examples used for PPI: 200
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.9400000000000001, 'ARES_Confidence_Interval': [0.910, 0.970], 'Number_of_Examples_in_Evaluation_Set': 200, 'Ground_Truth_Performance': 0.93, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.935, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.9500000000000001, 'ARES_Confidence_Interval': [0.920, 0.980], 'Number_of_Examples_in_Evaluation_Set': 200, 'Ground_Truth_Performance': 0.94, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.955, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.96, 'ARES_Confidence_Interval': [0.935, 0.985], 'Number_of_Examples_in_Evaluation_Set': 200, 'Ground_Truth_Performance': 0.96, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 1.0, 'Annotated_Examples_used_for_PPI': 200}]
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ 
```
