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
