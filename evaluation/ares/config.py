from pathlib import Path
from ares import ARES

ROOT = Path(__file__).resolve().parents[2]  # sube de evaluation/ares/ a la raíz del repo
GOLD_TSV = str(ROOT / "evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv")

ppi_config = {
    "evaluation_datasets": [GOLD_TSV], # Cuando exista el agente, cambias solo evaluation_datasets por sus respuestas.
    "few_shot_examples_filepath": GOLD_TSV,
    "checkpoints": [],
    "llm_judge": "gpt-4o",
    "labels": ["Context_Relevance_Label", "Answer_Faithfulness_Label", "Answer_Relevance_Label"],
    "gold_label_path": GOLD_TSV,
}

ares = ARES(ppi=ppi_config)
results = ares.evaluate_RAG()
print(results)