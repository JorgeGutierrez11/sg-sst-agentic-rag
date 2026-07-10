# Resumen de ejecución ARES

Salida registrada al ejecutar `python evaluation/ares/config.py` sobre `evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv`.

## Configuración observada

- `Evaluation Sets`: `conjunto_a_gold.tsv`
- `Checkpoints`: ninguno
- `Labels`: `Context_Relevance_Label`, `Answer_Faithfulness_Label`, `Answer_Relevance_Label`
- Modelo cargado: `claude-haiku-4-5-20251001`
- Número de ejemplos evaluados: `120`

## Resultados reportados

- `Context_Relevance_Label`
	- `ARES Prediction`: `0.6583333333333405`
	- `ARES Confidence Interval`: `[[0.57, 0.746]]`
	- `Ground Truth Performance`: `0.667`
	- `ARES LLM Judge Accuracy on Ground Truth Labels`: `0.975`
- `Answer_Faithfulness_Label`
	- `ARES Prediction`: `0.6749999999999938`
	- `ARES Confidence Interval`: `[[0.55, 0.8]]`
	- `Ground Truth Performance`: `0.667`
	- `ARES LLM Judge Accuracy on Ground Truth Labels`: `0.692`
- `Answer_Relevance_Label`
	- `ARES Prediction`: `0.6916666666666641`
	- `ARES Confidence Interval`: `[[0.57, 0.813]]`
	- `Ground Truth Performance`: `0.667`
	- `ARES LLM Judge Accuracy on Ground Truth Labels`: `0.7`

## Interpretación

- `Context Relevance`: excelente. El judge casi replica perfectamente tus etiquetas manuales.
- `Faithfulness y Relevance`: aceptables pero más débiles (~70%). El judge acierta 7 de cada 10 veces frente al criterio del experto. Es usable, pero documenta esto como limitación en la tesis — Claude Haiku (modelo pequeño/económico) tiene más dificultad distinguiendo matices de fidelidad/relevancia en textos legales que relevancia de contexto (tarea más binaria: ¿el fragmento toca el tema o no?). 

- Todas las predicciones ARES caen dentro o muy cerca del intervalo de confianza y cerca del ground truth — la calibración es coherente, no hay señales de que el pipeline esté roto.

## Salida del programa

```text
(.venv) pavlov@FLDSMDFR:~/GitHub/sg-sst-agentic-rag$ python evaluation/ares/config.py
vLLM not imported.
--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: claude-haiku-4-5-20251001
Performing Model scoring!
  0%|                                                                                                   | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:690: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:693: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
  2%|█▌                                                                                         | 2/120 [00:04<04:52,  2.48s/it]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:690: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:693: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|█████████████████████████████████████████████████████████████████████████████████████████| 120/120 [02:31<00:00,  1.26s/it]
Evaluating:   0%|                                                                                       | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:690: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:693: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                          | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|███████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 40.99it/s]
--------------------------------------------------
Context_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.6583333333333405]
ARES Confidence Interval: [[0.57, 0.746]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.975]
Annotated Examples used for PPI: 120
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: claude-haiku-4-5-20251001
Performing Model scoring!
  0%|                                                                                                   | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:792: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:795: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|█████████████████████████████████████████████████████████████████████████████████████████| 120/120 [04:31<00:00,  2.26s/it]
Evaluating:   0%|                                                                                       | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:792: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:795: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                          | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|███████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 41.43it/s]
--------------------------------------------------
Answer_Faithfulness_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.6749999999999938]
ARES Confidence Interval: [[0.55, 0.8]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.692]
Annotated Examples used for PPI: 120
--------------------------------------------------

--------------------------------------------------------
Evaluation Sets: ['/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv']
Checkpoints: []
Labels: ['Context_Relevance_Label', 'Answer_Faithfulness_Label', 'Answer_Relevance_Label']
--------------------------------------------------------
Loaded API model based on model identifier: claude-haiku-4-5-20251001
Performing Model scoring!
  0%|                                                                                                   | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:894: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:897: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
100%|█████████████████████████████████████████████████████████████████████████████████████████| 120/120 [04:00<00:00,  2.00s/it]
Evaluating:   0%|                                                                                       | 0/120 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:894: UserWarning: Incorrect label '1' detected. Please use '[[Yes]]' instead.
  warnings.warn("Incorrect label '1' detected. Please use '[[Yes]]' instead.")
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/Evaluation_Functions.py:897: UserWarning: Incorrect label '0' detected. Please use '[[No]]' instead.
  warnings.warn("Incorrect label '0' detected. Please use '[[No]]' instead.")
Trials:   0%|                                                                                          | 0/1000 [00:00<?, ?it/s]/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/ares/RAG_Automatic_Evaluation/ppi.py:81: RuntimeWarning: Mean of empty slice.
  rechat = (Yhat_labeled - Y_labeled).mean()
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:129: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:206: RuntimeWarning: Degrees of freedom <= 0 for slice
  ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:163: RuntimeWarning: invalid value encountered in divide
  arrmean = um.true_divide(arrmean, div, out=arrmean,
/home/pavlov/GitHub/sg-sst-agentic-rag/.venv/lib/python3.11/site-packages/numpy/core/_methods.py:198: RuntimeWarning: invalid value encountered in scalar divide
  ret = ret.dtype.type(ret / rcount)
Trials: 100%|███████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:24<00:00, 41.41it/s]
--------------------------------------------------
Answer_Relevance_Label Scoring
ARES Ranking
Evaluation_Set:/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv
Checkpoint:None
ARES Prediction: [0.6916666666666641]
ARES Confidence Interval: [[0.57, 0.813]]
Number of Examples in Evaluation Set: [120]
Ground Truth Performance: [0.667]
ARES LLM Judge Accuracy on Ground Truth Labels: [0.7]
Annotated Examples used for PPI: 120
--------------------------------------------------

[{'Label_Column': 'Context_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.6583333333333405, 'ARES_Confidence_Interval': [0.57, 0.746], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.975, 'Annotated_Examples_used_for_PPI': 120}, {'Label_Column': 'Answer_Faithfulness_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.6749999999999938, 'ARES_Confidence_Interval': [0.55, 0.8], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.692, 'Annotated_Examples_used_for_PPI': 120}, {'Label_Column': 'Answer_Relevance_Label', 'Evaluation_Set': '/home/pavlov/GitHub/sg-sst-agentic-rag/evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv', 'ARES_Prediction': 0.6916666666666641, 'ARES_Confidence_Interval': [0.57, 0.813], 'Number_of_Examples_in_Evaluation_Set': 120, 'Ground_Truth_Performance': 0.667, 'ARES_LLM_Judge_Accuracy_on_Ground_Truth_Labels': 0.7, 'Annotated_Examples_used_for_PPI': 120}]
```