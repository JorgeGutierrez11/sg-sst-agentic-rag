from pathlib import Path
from dotenv import load_dotenv
from ares import ARES

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
GOLD_TSV = str(ROOT / "evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv")

ppi_config = {
    "evaluation_datasets": [GOLD_TSV],
    "few_shot_examples_filepath": str(ROOT / "evaluation/datasets/conjunto_a_gold/fewshot_subset.tsv"),
    "checkpoints": [],
    "labels": ["Context_Relevance_Label", "Answer_Faithfulness_Label", "Answer_Relevance_Label"],
    "gold_label_paths": [GOLD_TSV],
    "llm_judge": "deepseek-v4-flash",
    "model_choice": "deepseek-v4-flash",
    #"llm_judge": "claude-haiku-4-5-20251001",
    #"model_choice": "claude-haiku-4-5-20251001",
    "rag_type": "question_answering",
}

ares = ARES(ppi=ppi_config)
results = ares.evaluate_RAG()
print(results)