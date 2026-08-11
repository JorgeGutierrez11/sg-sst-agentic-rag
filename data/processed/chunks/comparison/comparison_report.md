# Chunking Strategy Comparison

| Strategy | Chunks | Avg tokens | Too small | Too large | Unresolved offsets | Article metadata | Source metadata |
|---|---:|---:|---:|---:|---:|---:|---:|
| sliding_window | 417 | 190.2 | 28 | 0 | 0 | 93.05% | 100.0% |
| semantic_chunking | 282 | 267.96 | 56 | 70 | 165 | 95.74% | 100.0% |
| regex_constrained_semantic | 330 | 228.57 | 18 | 0 | 0 | 93.33% | 100.0% |

## Summary

{
  "available_strategies": 3,
  "most_chunks": "sliding_window",
  "fewest_oversized_chunks": "sliding_window",
  "fewest_unresolved_offsets": "sliding_window",
  "best_article_metadata_coverage": "semantic_chunking"
}
