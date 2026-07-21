# RAG Evaluation Findings 2

**Source:** Wikipedia Apollo 11 article (first 27 pages, references removed). **Embeddings:** text-embedding-3-small. **Chunks:** 500 chars, 100 overlap. **k:** 7. **Judge:** gpt-4.1-mini. **Dataset:** 72 questions (30 single_hop, 30 multi_hop, 6 false_premise, 6 out_of_scope).

Full raw results are in `test_results_findings_2/`.

## What changed from FINDINGS_1

ALDI's report was a weak source for multi-hop questions. Its sections don't reference each other. I switched to the Wikipedia Apollo 11 article, and generated the single_hop and multi_hop questions with RAGAS's `TestsetGenerator`, instead of writing them by hand. I kept the false_premise and out_of_scope questions hand-written, because RAGAS doesn't generate those.

I ran the eval 3 times to check how consistent the results are.

## Results (average of 3 runs)

| | single_hop | multi_hop |
|---|---|---|
| faithfulness | 0.83 | 0.84 |
| relevancy | 0.84 | 0.81 |
| recall | 0.73 | 0.64 |

Out-of-scope refusal: 18/18 (100%).
False-premise correction: 7/18 (39%).

## Findings

**Multi-hop recall is still lower than single-hop recall (0.64 vs 0.73).** This is the same gap as in FINDINGS_1. Now it is confirmed on a different document and a different, RAGAS-generated question set. A single retrieval pass has trouble pulling chunks from several distant sections at the same time. Query decomposition or re-ranking would probably fix this.

**False-premise correction is inconsistent (39%), but recall is 1.0 in every run.** The retriever always finds the fact needed to correct the false premise. The model just doesn't use it. When it fails, it answers "I don't know based on the available documents", instead of engaging with the question. This looks like a prompt issue. The system prompt only tells the model to answer from context or refuse. It never tells the model what to do if the premise itself is wrong.

## Next step

Add an instruction to the system prompt for handling false premises, then test again. I would like to test only one change at a time, so I won't implement query decomposition or re-ranking now.