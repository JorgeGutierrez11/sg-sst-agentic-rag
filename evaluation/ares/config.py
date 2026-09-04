from pathlib import Path
from dotenv import load_dotenv
from ares import ARES

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
GOLD_TSV = str(ROOT / "evaluation/datasets/conjunto_a_gold/conjunto_a_gold.tsv")
EVALUATION_TSV = str(ROOT / "evaluation/results/ares_runs/retrieval/hybrid_reranking.tsv")

ppi_config = {
    "evaluation_datasets": [EVALUATION_TSV],
    "few_shot_examples_filepath": str(ROOT / "evaluation/datasets/conjunto_a_gold/fewshot_subset.tsv"),
    "checkpoints": [],
    "labels": ["Context_Relevance_Label", "Answer_Faithfulness_Label", "Answer_Relevance_Label"],
    "gold_label_paths": [GOLD_TSV],
    "llm_judge": "deepseek-v4-flash",
    "model_choice": "deepseek-v4-flash",
    "rag_type": "question_answering",
}

ares = ARES(ppi=ppi_config)
results = ares.evaluate_RAG()
print(results)