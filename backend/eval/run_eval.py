import json
import asyncio
import os
import sys
import math
from collections import defaultdict
from datetime import datetime
from typing import TypedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()
os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace("@db:", "@localhost:")

from app.repositories.document_repository import DocumentRepository
from app.services.retrieval_service import RetrievalService
from openai import AsyncOpenAI
from ragas import SingleTurnSample, EvaluationDataset
from ragas.llms import llm_factory
from ragas.embeddings import OpenAIEmbeddings
from ragas.metrics.collections import Faithfulness, AnswerRelevancy, ContextRecall


class Result(TypedDict):
    question: str
    type: str
    faithfulness: float
    answer_relevancy: float
    context_recall: float
    refused: bool


class RawSample(TypedDict):
    question: str
    ground_truth: str
    type: str


client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm = llm_factory("gpt-4.1-mini", client=client)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", client=client)

repo = DocumentRepository()
service = RetrievalService(repo)

faithfulness_metric = Faithfulness(llm=llm)
relevancy_metric = AnswerRelevancy(llm=llm, embeddings=embeddings)
recall_metric = ContextRecall(llm=llm)

semaphore = asyncio.Semaphore(11)

with open("eval/test_dataset.json") as f:
    raw: list[RawSample] = json.load(f)


def mean(xs: list[float]) -> float:
    xs = [x for x in xs if not math.isnan(x)]
    return sum(xs) / len(xs) if xs else float("nan")


def type_breakdown(results: list[Result]) -> str:
    by_type: dict[str, list[Result]] = defaultdict(list)
    for r in results:
        by_type[r["type"]].append(r)
    lines: list[str] = []
    for t in sorted(by_type):
        rows = by_type[t]
        lines.append(f"[{t}] (n={len(rows)})")
        if t == "out_of_scope":
            n_ref = sum(1 for x in rows if x["refused"])
            lines.append(f"  correct refusals={n_ref}/{len(rows)} ({n_ref / len(rows):.0%})")
        else:
            f_ = mean([x["faithfulness"] for x in rows])
            r_ = mean([x["answer_relevancy"] for x in rows])
            c_ = mean([x["context_recall"] for x in rows])
            lines.append(f"  faithfulness={f_:.3f}  relevancy={r_:.3f}  recall={c_:.3f}")
    return "\n".join(lines)


async def build_one(s: RawSample) -> tuple[SingleTurnSample, str]:
    docs = await asyncio.to_thread(repo.similarity_search, s["question"])
    contexts: list[str] = [doc.page_content for doc in docs]
    result = await service.answer(s["question"], [])
    sample = SingleTurnSample(
        user_input=s["question"],
        response=result["answer"],
        retrieved_contexts=contexts,
        reference=s["ground_truth"],
    )
    return sample, s.get("type", "unknown")


async def build_all() -> tuple[list[SingleTurnSample], list[str]]:
    pairs = await asyncio.gather(*[build_one(s) for s in raw])
    return [p[0] for p in pairs], [p[1] for p in pairs]


async def score_sample(sample: SingleTurnSample, qtype: str) -> Result:
    async with semaphore:
        faith, relevancy, recall = await asyncio.gather(
            faithfulness_metric.ascore(  # type: ignore[call-arg]
                user_input=sample.user_input, response=sample.response, retrieved_contexts=sample.retrieved_contexts  # type: ignore[union-attr]
            ),
            relevancy_metric.ascore(  # type: ignore[call-arg]
                user_input=sample.user_input, response=sample.response  # type: ignore[union-attr]
            ),
            recall_metric.ascore(  # type: ignore[call-arg]
                user_input=sample.user_input,  # type: ignore[union-attr]
                retrieved_contexts=sample.retrieved_contexts, reference=sample.reference  # type: ignore[union-attr]
            ),
        )
        f, r, c = faith.value, relevancy.value, recall.value  # type: ignore[union-attr]
        refused = "based on the available documents" in sample.response.lower()  # type: ignore[union-attr]
        print(f"✓ [{qtype}] {sample.user_input[:60]}")  # type: ignore[union-attr]
        print(f"  faithfulness={f:.2f}  relevancy={r:.2f}  recall={c:.2f}")
        return {"question": sample.user_input, "type": qtype, "faithfulness": f, "answer_relevancy": r, "context_recall": c, "refused": refused}  # type: ignore[union-attr]


async def run_eval() -> None:
    samples, types = await build_all()
    dataset = EvaluationDataset(samples=samples)  # type: ignore[arg-type]

    results: list[Result] = await asyncio.gather(*[score_sample(s, t) for s, t in zip(dataset.samples, types)])  # type: ignore[union-attr]

    answerable = [r for r in results if r["type"] != "out_of_scope"]
    oos = [r for r in results if r["type"] == "out_of_scope"]
    n_refused = sum(1 for r in oos if r["refused"])
    avg_faith = mean([r["faithfulness"] for r in answerable])
    avg_rel = mean([r["answer_relevancy"] for r in answerable])
    avg_rec = mean([r["context_recall"] for r in answerable])
    print(f"\n=== AVERAGES (answerable only, n={len(answerable)}) ===")
    print(f"faithfulness:     {avg_faith:.3f}")
    print(f"answer_relevancy: {avg_rel:.3f}")
    print(f"context_recall:   {avg_rec:.3f}")
    if oos:
        print(f"\n=== REFUSAL (out_of_scope) ===")
        print(f"correct refusals: {n_refused}/{len(oos)} ({n_refused / len(oos):.0%})")
    print(f"\n=== PER TYPE ===")
    print(type_breakdown(results))

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.path.dirname(__file__), f"results_{timestamp}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"=== EVAL RUN METADATA ===\n")
        f.write(f"Run:       {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model:     {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}\n")
        f.write(f"Embedding: {os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')}\n")
        f.write(f"Samples:   {len(results)}\n\n")
        f.write(f"=== PER QUESTION ===\n")
        for r in results:
            f.write(f"[{r['type']}] {r['question']}\n")
            if r["type"] == "out_of_scope":
                f.write(f"  {'refused ✓' if r['refused'] else 'NOT refused ✗'}  (generation metrics n/a)\n\n")
            else:
                warning = "  ⚠" if (r["faithfulness"] < 0.7 or r["answer_relevancy"] < 0.7 or r["context_recall"] < 0.7) else ""
                f.write(f"  faithfulness={r['faithfulness']:.2f}  relevancy={r['answer_relevancy']:.2f}  recall={r['context_recall']:.2f}{warning}\n\n")
        f.write(f"=== AVERAGES (answerable only, n={len(answerable)}) ===\n")
        f.write(f"faithfulness:     {avg_faith:.3f}\n")
        f.write(f"answer_relevancy: {avg_rel:.3f}\n")
        f.write(f"context_recall:   {avg_rec:.3f}\n")
        if oos:
            f.write(f"\n=== REFUSAL (out_of_scope) ===\n")
            f.write(f"correct refusals: {n_refused}/{len(oos)} ({n_refused / len(oos):.0%})\n")
        f.write(f"\n=== PER TYPE ===\n")
        f.write(type_breakdown(results) + "\n")
    print(f"\nResults saved to {output_path}")


asyncio.run(run_eval())
