import os
import json
from typing import TypedDict

from dotenv import load_dotenv
load_dotenv()

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers.testset_schema import Testset

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class RawSample(TypedDict):
    question: str
    ground_truth: str
    type: str


SYNTHESIZER_TYPE_MAP = {
    "single_hop_specific_query_synthesizer": "single_hop",
    "multi_hop_specific_query_synthesizer": "multi_hop",
    "multi_hop_abstract_query_synthesizer": "multi_hop",
}

RAGAS_CACHE_PATH = "eval/ragas_raw.json"
OUTPUT_PATH = "eval/test_dataset_apollo.json"



def load_or_generate_ragas_samples() -> list[RawSample]:
    if os.path.exists(RAGAS_CACHE_PATH):
        with open(RAGAS_CACHE_PATH, encoding="utf-8") as f:
            rows = json.load(f)
    else:
        loader = PyMuPDFLoader("eval/apollo_11.pdf")
        docs = loader.load()[:27]
        merged_text = "\n\n".join(doc.page_content for doc in docs)
        docs = [Document(page_content=merged_text, metadata={"filename": "apollo_11"})]

        llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4.1-mini"))
        embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
        generator = TestsetGenerator(llm=llm, embedding_model=embeddings)

        testset = generator.generate_with_langchain_docs(docs, testset_size=60)
        assert isinstance(testset, Testset)
        df = testset.to_pandas()

        rows = df[["user_input", "reference", "synthesizer_name"]].to_dict(orient="records")
        with open(RAGAS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    return [
        RawSample(
            question=str(row["user_input"]),
            ground_truth=str(row["reference"]),
            type=str(SYNTHESIZER_TYPE_MAP.get(row["synthesizer_name"], row["synthesizer_name"])),
        )
        for row in rows
    ]


false_premise_questions: list[RawSample] = [
    {
        "question": "Why was Buzz Aldrin the first person to walk on the Moon?",
        "ground_truth": "This premise is incorrect — Neil Armstrong was "
        "actually the first to walk on the Moon, with Aldrin being the second, nineteen minutes later.",
        "type": "false_premise",
    },
    {
        "question": "Why was the Lunar Module named Columbia?",
        "ground_truth": "This premise is incorrect — Columbia was the name of the Command Module; the Lunar Module was named Eagle.",
        "type": "false_premise",
    },
    {
        "question": "Why did Michael Collins land on the Moon alongside Armstrong?",
        "ground_truth": "This premise is incorrect — Michael Collins remained in lunar orbit aboard the Command Module Columbia; only Armstrong and Aldrin descended to the surface.",
        "type": "false_premise",
    },
    {
        "question": "Why did the Apollo 11 crew fail to return safely to Earth?",
        "ground_truth": "This premise is incorrect — the crew returned safely to Earth on July 24, 1969.",
        "type": "false_premise",
    },
    {
        "question": "Why was Michael Collins the commander of the Apollo 11 mission?",
        "ground_truth": "This premise is incorrect — Neil Armstrong was the Commander; Michael Collins served as the Command Module Pilot.",
        "type": "false_premise",
    },
    {
        "question": "Why did Apollo 11 land in the Sea of Serenity?",
        "ground_truth": "This premise is incorrect — Apollo 11 landed in the Sea of Tranquility (Mare Tranquillitatis), at a site named Tranquility Base.",
        "type": "false_premise",
    },
]

out_of_scope_questions: list[RawSample] = [
    {
        "question": "How much did NASA's Space Shuttle program cost in total?",
        "ground_truth": "I don't know based on the available documents.",
        "type": "out_of_scope",
    },
    {
        "question": "What is the capital of Hungary?",
        "ground_truth": "I don't know based on the available documents.",
        "type": "out_of_scope",
    },
    {
        "question": "How many people currently live and work aboard the International Space Station?",
        "ground_truth": "I don't know based on the available documents.",
        "type": "out_of_scope",
    },
    {
        "question": "What safety modifications were made to the Space Shuttle after the Challenger disaster?",
        "ground_truth": "I don't know based on the available documents.",
        "type": "out_of_scope",
    },
    {
        "question": "What was the cause of the oxygen tank failure during the Apollo 13 mission?",
        "ground_truth": "I don't know based on the available documents.",
        "type": "out_of_scope",
    },
    {
        "question": "What is NASA's current budget for the Artemis Moon program?",
        "ground_truth": "I don't know based on the available documents.",
        "type": "out_of_scope",
    },
]


def main() -> None:
    ragas_samples = load_or_generate_ragas_samples()
    all_samples: list[RawSample] = ragas_samples + false_premise_questions + out_of_scope_questions

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    print(f"Mentve: {len(all_samples)} kérdés -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()