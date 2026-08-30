# Resumen de ejecución ARES — deepseek-v4-flash

**Fecha:** 24-08-2026

**Comando:** `python evaluation/ares/config.py`

**Observaciones generales:**
- Mensaje: `vLLM not imported.`
- Advertencias sobre formato de etiquetas: se detectaron etiquetas '1'/'0' (usar `[[Yes]]`/`[[No]]`).
- Advertencias NumPy/PPI durante simulaciones (valores NaN / varianza cero) — revisar conjunto anotado.

**Conjunto de evaluación:** evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv (120 ejemplos)

---

**Métricas por etiqueta**

- Context_Relevance_Label
	- ARES Prediction: 0.6833
	- Intervalo de confianza ARES: [0.584, 0.783]
	- Ground truth (performance del modelo): 0.667
	- Exactitud del juez ARES sobre etiquetas ground-truth: 0.95
	- Ejemplos usados: 120

- Answer_Faithfulness_Label
	- ARES Prediction: 0.6583
	- Intervalo de confianza ARES: [0.539, 0.777]
	- Ground truth: 0.667
	- Exactitud del juez ARES sobre etiquetas ground-truth: 0.658
	- Ejemplos usados: 120

- Answer_Relevance_Label
	- ARES Prediction: 0.6750
	- Intervalo de confianza ARES: [0.557, 0.793]
	- Ground truth: 0.667
	- Exactitud del juez ARES sobre etiquetas ground-truth: 0.775
	- Ejemplos usados: 120

---

**Síntesis corta:**
ARES predice un rendimiento ligeramente superior al ground-truth (~0.66–0.68) en las tres etiquetas. Sin embargo, las advertencias sobre el formato de etiquetas y las advertencias numéricas durante PPI sugieren que conviene corregir el formato de etiquetas (`[[Yes]]`/`[[No]]`) y revisar los ejemplos anotados usados para PPI antes de interpretar los intervalos y las simulaciones.

**NOtas:**
- Esto es porque el modelo dice 1 y 0 pero ares tiene su propio parser asi que si entiende 1 y 0 `[[Yes]]`/`[[No]]`.


## Salida del programa

```text
pavlov@FLDSMDFR:/GitHub/sg-sst-agentic-rag$ source /home/pavlov/GitHub/sg-sst-agentic-rag/.venv/bin/activate
(.venv) pavlov@FLDSMDFR:/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
0%| | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
2%|█▍ | 2/120 [00:11<11:42, 5.95s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████| 120/120 [10:29<00:00, 5.25s/it]
Evaluating: 0%| | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials: 0%| | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
ret = ret.dtype.type(ret / rcount)
Trials: 100%|█████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.42it/s]
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.68333333333333]
ARES Confidence Interval: [[0.584, 0.783]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.95]
Annotated Examples used for PPI: 120
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
0%| | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████| 120/120 [06:40<00:00, 3.33s/it]
Evaluating: 0%| | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials: 0%| | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
ret = ret.dtype.type(ret / rcount)
Trials: 100%|█████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.24it/s]
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.6583333333333339]
ARES Confidence Interval: [[0.539, 0.777]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.658]
Annotated Examples used for PPI: 120
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
0%| | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|███████████████████████████████████████████████████████████████████████████████████| 120/120 [09:53<00:00, 4.94s/it]
Evaluating: 0%| | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials: 0%| | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
ret = ret.dtype.type(ret / rcount)
Trials: 100%|█████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.06it/s]
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.6750000000000003]
ARES Confidence Interval: [[0.557, 0.793]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.775]
Annotated Examples used for PPI: 120
[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.68333333333333, 'ARES_Confidence_Interval': [0.584, 0.783], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.95, 'Annotated_Examples_used_for_PPI': 120}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.6583333333333339, 'ARES_Confidence_Interval': [0.539, 0.777], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.658, 'Annotated_Examples_used_for_PPI': 120}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.6750000000000003, 'ARES_Confidence_Interval': [0.557, 0.793], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.775, 'Annotated_Examples_used_for_PPI': 120}]
```



# segunda prueba

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
  0%|                                                                                                            | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  2%|█▋                                                                                                  | 2/120 [00:16<16:09,  8.21s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|██████████████████████████████████████████████████████████████████████████████████████████████████| 120/120 [19:10<00:00,  9.58s/it]
Evaluating:   0%|                                                                                                | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:94: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:97: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 39.22it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.7249999999999971]
ARES Confidence Interval: [[0.632, 0.818]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.9]
Annotated Examples used for PPI: 120
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                            | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|██████████████████████████████████████████████████████████████████████████████████████████████████| 120/120 [04:40<00:00,  2.34s/it]
Evaluating:   0%|                                                                                                | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:191: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:194: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:25<00:00, 39.81it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.34166666666666834]
ARES Confidence Interval: [[0.255, 0.429]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.333]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.992]
Annotated Examples used for PPI: 120
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: deepseek-v4-flash
Performing Model scoring!
  0%|                                                                                                            | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|██████████████████████████████████████████████████████████████████████████████████████████████████| 120/120 [09:13<00:00,  4.62s/it]
Evaluating:   0%|                                                                                                | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:288: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:291: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                                   | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 41.02it/s]
--------------------------------------------------
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.6166666666666774]
ARES Confidence Interval: [[0.501, 0.732]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.725]
Annotated Examples used for PPI: 120
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.7249999999999971, 'ARES_Confidence_Interval': [0.632, 0.818], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.9, 'Annotated_Examples_used_for_PPI': 120}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.34166666666666834, 'ARES_Confidence_Interval': [0.255, 0.429], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.333, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.992, 'Annotated_Examples_used_for_PPI': 120}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.6166666666666774, 'ARES_Confidence_Interval': [0.501, 0.732], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.725, 'Annotated_Examples_used_for_PPI': 120}]
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ 
```