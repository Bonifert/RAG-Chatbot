# RAG Evaluation Findings 3

**Source:** Wikipedia Apollo 11 article (same as FINDINGS_2). **Embeddings:** text-embedding-3-small. **Chunks:** 500 chars, 100 overlap. **k:** 7. **Judge:** gpt-4.1-mini. **Dataset:** same 72 question set as FINDINGS_2 (30 single_hop, 30 multi_hop, 6 false_premise, 6 out_of_scope).

Full raw results are in `test_results_findings_3/`. Two of the three runs only used the 6 false_premise questions, not all 72. The table below shows which run covered what.

## What changed from FINDINGS_2

In FINDINGS_2, false premise correction was not consistent (39%), even though the retriever always found the right fact. The system prompt only told the model to answer from context or say "I don't know". It never said what to do when the question itself was wrong. I added one line to the system prompt: "If the question assumes something that contradicts the context, say so and give the correct fact from the context."

I also added an option to run the eval on just one question type. This way I can test the false_premise questions without running all 72 questions every time.

## Results

I ran the false_premise questions twice on their own, then ran the full dataset once to check the other question types were still fine.

| | run 1 | run 2 | full run |
|---|---|---|---|
| false premise correction | 6/6 (100%) | 6/6 (100%) | 6/6 (100%) |
| faithfulness | 1.000 | 1.000 | 0.979 |
| relevancy | 0.778 | 0.744 | 0.767 |
| recall | 1.000 | 1.000 | 1.000 |

Full run, other question types compared to the FINDINGS_2 averages:

| | FINDINGS_2 (avg of 3 runs) | FINDINGS_3 (1 run) |
|---|---|---|
| single_hop faithfulness | 0.83 | 0.891 |
| single_hop relevancy | 0.84 | 0.819 |
| single_hop recall | 0.73 | 0.734 |
| multi_hop faithfulness | 0.84 | 0.813 |
| multi_hop relevancy | 0.81 | 0.790 |
| multi_hop recall | 0.64 | 0.613 |

Out-of-scope refusal: 6/6 (100%), same as before.

## Findings

The prompt change worked for false premise correction. All three runs got 6/6, up from 7/18 (39%) in FINDINGS_2. Recall was already 1.0 before the change too, so the retriever was never really the issue, the model just needed a clear instruction for what to do.

The other question types stayed about the same. Single_hop and multi_hop numbers from the full run are close to the FINDINGS_2 averages, and the small differences are normal between runs.

Multi_hop recall is still low, 0.61 to 0.64 in both findings, but this is expected, as this change doesn't affect the multi_hop or single_hop recalls.

Single_hop recall (0.73) is also low, but not as much as multi_hop, so I will focus on multi_hop.

## Next step

False premise handling looks solved for now. Multi_hop recall is the next thing to fix, since it's the lowest score overall.

I want to try query decomposition first, because I think it can help a lot with multi_hop recall.

Re-ranking probably won't help much here. It only sorts and picks from chunks that already got retrieved, it can't bring back a chunk that was never retrieved. Since recall is the actual problem, re-ranking doesn't really help.

If decomposition alone isn't enough, tuning the chunking is probably the better change, not re-ranking. It might also help with the single_hop recall issue, which decomposition won't touch since a single_hop question doesn't need splitting.
