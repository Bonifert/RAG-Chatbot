# RAG Evaluation Findings

**PDF:** ALDI 2024 Sustainability Report · **Embeddings:** text-embedding-3-small · **Chunks:** 500 chars, 100 overlap · **Dataset:** 21 questions (13 single_hop, 6 multi_hop, 2 out_of_scope)

---
You can find the raw test results in the test_results_findings_1 folder

## What I measured

I used RAGAS with three metrics: faithfulness, answer relevancy, and context recall.

The first runs used gpt-4o-mini as both the app model and the judge. Later I switched the judge to gpt-4.1-mini, since a stronger model judges more strictly. Generally better to use a stronger judge than the model you're testing, so it's not grading its own homework.


## Retrieval tuning (k = number of retrieved chunks)

Faithfulness, answer relevancy, and single_hop recall stayed consistently high (roughly 0.85-1.00) across every k value and both judges, so these weren't a concern. Multi_hop recall was the only metric that moved meaningfully with k, so that's what this section focuses on.

Multi_hop questions need info from several parts of the PDF, so I tested different k values.
Each k was run multiple times; the table shows the median multi_hop recall.

**Judge: gpt-4o-mini**

| k | runs | multi_hop recall (median) |
|---|---|---|
| 4 | 4 | 0.54 |
| 6 | 4 | 0.65 |
| **7** | 3 | **0.68** |
| 8 | 2 | 0.59 |

**Judge: gpt-4.1-mini**

| k | runs | multi_hop recall (median) |
|---|---|---|
| 6 | 3 | 0.54 |
| **7** | 3 | **0.57** |
| 8 | 2 | 0.53 |

k=7 wins with both judges. At k=8 performance drops because the extra chunks add noise.

## Final config: k=7, judge: gpt-4.1-mini

| Metric | single_hop | multi_hop | overall |
|---|---|---|---|
| faithfulness | 1.000 | 0.970 | 0.997 |
| answer_relevancy | 0.880 | 0.968 | 0.908 |
| context_recall | 0.962 | 0.567 | 0.837 |

Out-of-scope refusal: **2/2 (100%)**


## Why multi_hop recall is low

~0.57 is probably the ceiling for this setup. The problem is that one query can't reliably pull chunks from several distant sections at the same time. Tuning k helps a bit but doesn't fix the root cause.

The proper fix would be query decomposition: break the question into sub-questions, retrieve each separately, then combine the results or another option would be re-ranking: retrieve a high top-k, then rerank the results with another LLM call.


## Test dataset

The ALDI sustainability report was not a good source for multi-hop questions. The report has separate facts in each section, and the sections don't really connect to each other, so it was hard to write good multi-hop questions from it.


## Next step

I will use a different PDF, and let RAGAS generate the test set automatically. I won't implement the query decomposition or re-ranking yet. First, I would like to test the RAG chatbot with better test data.