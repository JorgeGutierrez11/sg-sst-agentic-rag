# Resultados ARES - B2 Antes

## Resumen Ejecutivo

Se evaluaron 80 ejemplos del set `b2_antes_ares.tsv` con el juez LLM `deepseek-v4-flash` en tres dimensiones: relevancia de contexto, fidelidad de respuesta y relevancia de respuesta.

Los resultados son altos en terminos generales, pero se mantienen alertas metodologicas observadas en corridas previas:

1. Etiquetas en formato `0/1` en lugar de `[[No]]/[[Yes]]`.
2. Predicciones e intervalos de confianza que exceden 1.0 en algunas metricas.

## Configuracion de la Corrida

| Campo | Valor |
|---|---|
| Evaluation Set | `/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv` |
| Modelo juez (API) | `deepseek-v4-flash` |
| Labels evaluadas | `Context_Relevance_Label`, `Answer_Faithfulness_Label`, `Answer_Relevance_Label` |
| Ejemplos en set | `80` |
| Ejemplos anotados para PPI | `200` |

## Resultados Principales

| Metrica | Prediccion ARES | IC ARES (95%) | Ground Truth | Accuracy juez vs GT |
|---|---:|---:|---:|---:|
| Context_Relevance_Label | 0.9400 | [0.88, 1.00] | 1.0000 | 0.925 |
| Answer_Faithfulness_Label | 1.2225 | [1.159, 1.286] | 1.0000 | 0.988 |
| Answer_Relevance_Label | 0.9875 | [0.963, 1.012] | 1.0000 | 0.988 |

## Hallazgos y Alertas Tecnicas

| Hallazgo | Evidencia | Impacto |
|---|---|---|
| Formato de etiquetas no estandar | Warnings repetidos: usar `[[Yes]]/[[No]]` en vez de `1/0` | Riesgo de sesgo o interpretacion incorrecta en evaluacion automatica |
| Prediccion > 1.0 en fidelidad | `Answer_Faithfulness_Label = 1.2225` | Valor fuera de rango esperado para metrica tipo proporcion; revisar calibracion/PPI |
| Limites de IC > 1.0 | `Answer_Faithfulness` y `Answer_Relevance` incluyen valores por encima de 1.0 | Posible problema de calibracion/estimacion que afecta interpretabilidad |
| Warnings numericos en PPI | `Mean of empty slice`, `invalid value encountered` | Posible inestabilidad estadistica en subcalculos |

## salida

```text
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                                             | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  2%|██▉                                                                                                                  | 2/80 [00:03<02:26,  1.88s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [04:06<00:00,  3.08s/it]
Evaluating:   0%|                                                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 41.23it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv
Checkpoint:None
ARES Prediction: [0.9399999999999983]
ARES Confidence Interval: [[0.88, 1.0]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.925]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                                             | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [05:13<00:00,  3.92s/it]
Evaluating:   0%|                                                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.87it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv
Checkpoint:None
ARES Prediction: [1.2225000000000086]
ARES Confidence Interval: [[1.159, 1.286]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.988]
Annotated Examples used for PPI: 200
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                                             | 0/80 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 80/80 [03:59<00:00,  2.99s/it]
Evaluating:   0%|                                                                                                                | 0/200 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 39.35it/s]
--------------------------------------------------
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv
Checkpoint:None
ARES Prediction: [0.9875000000000071]
ARES Confidence Interval: [[0.963, 1.012]]
Number of Examples in Evaluation Set: [80]
Ground Truth Performance: [1.0]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.988]
Annotated Examples used for PPI: 200
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv', 'ARES_Prediction': 0.9399999999999983, 'ARES_Confidence_Interval': [0.88, 1.0], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.925, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv', 'ARES_Prediction': 1.2225000000000086, 'ARES_Confidence_Interval': [1.159, 1.286], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.988, 'Annotated_Examples_used_for_PPI': 200}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/results/Actividad 3. Ares/ares runs/b2_antes_ares.tsv', 'ARES_Prediction': 0.9875000000000071, 'ARES_Confidence_Interval': [0.963, 1.012], 'Number_of_Examples_in_Evaluation_Set': 80, 'Ground_Truth_Performance': 1.0, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.988, 'Annotated_Examples_used_for_PPI': 200}]
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ 
```
