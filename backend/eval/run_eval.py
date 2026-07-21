import json
import asyncio
import os
import sys
import math
from collections import defaultdict
from datetime import datetime
from typing import TypedDict
from typing import TextIO
import argparse

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
from pydantic import BaseModel


class Result(TypedDict):
    question: str
    type: str
    faithfulness: float
    answer_relevancy: float
    context_recall: float
    refused: bool
    corrected: bool
    answer: str


class RawSample(TypedDict):
    question: str
    ground_truth: str
    type: str


class CorrectionCheck(BaseModel):
    corrected_false_premise: bool


LLM_MODEL = "gpt-4.1-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm = llm_factory(LLM_MODEL, client=client, max_tokens=4096)
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, client=client)

repo = DocumentRepository()
service = RetrievalService(repo)

faithfulness_metric = Faithfulness(llm=llm)
relevancy_metric = AnswerRelevancy(llm=llm, embeddings=embeddings)
recall_metric = ContextRecall(llm=llm)

semaphore = asyncio.Semaphore(9)

parser = argparse.ArgumentParser()
parser.add_argument("--types", type=str, default=None, help="Comma-separated list of types to run, e.g. false_premise,out_of_scope")
args = parser.parse_args()
selected_types = set(args.types.split(",")) if args.types else None

with open("eval/test_dataset_apollo.json") as f:
    raw: list[RawSample] = json.load(f)

if selected_types and selected_types != {"all"}:
    raw = [r for r in raw if r["type"] in selected_types]

assert raw, "no sample matched --types"


def mean(values: list[float]) -> float:
    values = [v for v in values if not math.isnan(v)]
    return sum(values) / len(values) if values else float("nan")


async def check_false_premise_correction(question: str, response: str, reference: str) -> bool:
    prompt = f"""A user asked a question containing a FALSE premise (an incorrect assumption).
Question: {question}
Correct clarification: {reference}
System's actual response: {response}

Did the system's response correctly identify and correct the false premise (clearly stating the correct fact, not confirming or ignoring the false assumption)?
"""
    result = await llm.agenerate(prompt, CorrectionCheck)
    return result.corrected_false_premise


def type_breakdown(results: list[Result]) -> str:
    by_type: dict[str, list[Result]] = defaultdict(list)
    for result in results:
        by_type[result["type"]].append(result)
    lines: list[str] = []
    for qtype in sorted(by_type):
        rows = by_type[qtype]
        lines.append(f"[{qtype}] (n={len(rows)})")
        if qtype == "out_of_scope":
            n_ref = sum(1 for x in rows if x["refused"])
            lines.append(f"  correct refusals={n_ref}/{len(rows)} ({n_ref / len(rows):.0%})")
        elif qtype == "false_premise":
            n_corrected = sum(1 for x in rows if x["corrected"])
            lines.append(f"  correct corrections={n_corrected}/{len(rows)} ({n_corrected / len(rows):.0%})")
            lines.append(f"  faithfulness={mean([x['faithfulness'] for x in rows]):.3f}  relevancy={mean([x['answer_relevancy'] for x in rows]):.3f}  recall={mean([x['context_recall'] for x in rows]):.3f}")
        else:
            faithfulness = mean([x["faithfulness"] for x in rows])
            relevancy = mean([x["answer_relevancy"] for x in rows])
            recall = mean([x["context_recall"] for x in rows])
            lines.append(f"  faithfulness={faithfulness:.3f}  relevancy={relevancy:.3f}  recall={recall:.3f}")
    return "\n".join(lines)


async def build_one(raw_sample: RawSample) -> tuple[SingleTurnSample, str]:
    docs = await asyncio.to_thread(repo.similarity_search, raw_sample["question"])
    contexts: list[str] = [doc.page_content for doc in docs]
    result = await service.answer(raw_sample["question"], [])
    sample = SingleTurnSample(
        user_input=raw_sample["question"],
        response=result["answer"],
        retrieved_contexts=contexts,
        reference=raw_sample["ground_truth"],
    )
    return sample, raw_sample.get("type", "unknown")


async def build_all() -> tuple[list[SingleTurnSample], list[str]]:
    pairs = await asyncio.gather(*[build_one(raw_sample) for raw_sample in raw])
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
        faith_score, relevancy_score, recall_score = faith.value, relevancy.value, recall.value  # type: ignore[union-attr]
        refused = "based on the available documents" in sample.response.lower() if qtype == "out_of_scope" else False  # type: ignore[union-attr]
        corrected = await check_false_premise_correction(sample.user_input, sample.response, sample.reference) if qtype == "false_premise" else False  # type: ignore[union-attr]
        print(f"✓ [{qtype}] {sample.user_input[:60]}")  # type: ignore[union-attr]
        print(f"  faithfulness={faith_score:.2f}  relevancy={relevancy_score:.2f}  recall={recall_score:.2f}")
        return {
            "question": sample.user_input,  # type: ignore[union-attr]
            "type": qtype,
            "faithfulness": faith_score,
            "answer_relevancy": relevancy_score,
            "context_recall": recall_score,
            "refused": refused,
            "corrected": corrected,
            "answer": sample.response,
        }


def write_result(file: TextIO, result: Result) -> None:
    file.write(f"[{result['type']}] {result['question']}\n")
    metrics = f"faithfulness={result['faithfulness']:.2f}  relevancy={result['answer_relevancy']:.2f}  recall={result['context_recall']:.2f}"
    if result["type"] == "out_of_scope":
        file.write(f"  {'refused ✓' if result['refused'] else 'NOT refused ✗'}  (generation metrics n/a)\n")
    elif result["type"] == "false_premise":
        file.write(f"  {'corrected ✓' if result['corrected'] else 'NOT corrected ✗'}  {metrics}\n")
    else:
        warning = "  ⚠" if (result["faithfulness"] < 0.7 or result["answer_relevancy"] < 0.7 or result["context_recall"] < 0.7) else ""
        file.write(f"  {metrics}{warning}\n")
    file.write(f"  answer: {result['answer']}\n\n")


async def run_eval() -> None:
    samples, types = await build_all()
    dataset = EvaluationDataset(samples=samples)  # type: ignore[arg-type]

    results: list[Result] = await asyncio.gather(*[score_sample(s, t) for s, t in zip(dataset.samples, types)])  # type: ignore[union-attr]

    answerable = [result for result in results if result["type"] not in ("out_of_scope", "false_premise")]
    out_of_scope_results = [result for result in results if result["type"] == "out_of_scope"]
    n_refused = sum(1 for result in out_of_scope_results if result["refused"])
    avg_faithfulness = mean([result["faithfulness"] for result in answerable])
    avg_relevancy = mean([result["answer_relevancy"] for result in answerable])
    avg_recall = mean([result["context_recall"] for result in answerable])
    breakdown = type_breakdown(results)

    print(f"\n=== AVERAGES (answerable only, n={len(answerable)}) ===")
    print(f"faithfulness:     {avg_faithfulness:.3f}")
    print(f"answer_relevancy: {avg_relevancy:.3f}")
    print(f"context_recall:   {avg_recall:.3f}")
    if out_of_scope_results:
        print(f"\n=== REFUSAL (out_of_scope) ===")
        print(f"correct refusals: {n_refused}/{len(out_of_scope_results)} ({n_refused / len(out_of_scope_results):.0%})")
    print(f"\n=== PER TYPE ===")
    print(breakdown)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.path.dirname(__file__), f"results_{timestamp}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"=== EVAL RUN METADATA ===\n")
        f.write(f"Run:       {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model:     {LLM_MODEL}")
        f.write(f"Embedding: {EMBEDDING_MODEL}")
        f.write(f"Samples:   {len(results)}\n\n")
        f.write(f"=== PER QUESTION ===\n")
        for result in results:
            write_result(file=f, result=result)
        f.write(f"=== AVERAGES (answerable only, n={len(answerable)}) ===\n")
        f.write(f"faithfulness:     {avg_faithfulness:.3f}\n")
        f.write(f"answer_relevancy: {avg_relevancy:.3f}\n")
        f.write(f"context_recall:   {avg_recall:.3f}\n")
        if out_of_scope_results:
            f.write(f"\n=== REFUSAL (out_of_scope) ===\n")
            f.write(f"correct refusals: {n_refused}/{len(out_of_scope_results)} ({n_refused / len(out_of_scope_results):.0%})\n")
        f.write(f"\n=== PER TYPE ===\n")
        f.write(breakdown + "\n")
    print(f"\nResults saved to {output_path}")


asyncio.run(run_eval())