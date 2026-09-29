import argparse
import json
import re
import time
from pathlib import Path
from statistics import mean
from typing import TypedDict

import httpx


class EvaluationQuestion(TypedDict):
    question: str
    expected_keyword: str
    expected_document: str


def load_questions(path: Path) -> list[EvaluationQuestion]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("The evaluation file must contain a non-empty JSON list.")
    return data


def evaluate(base_url: str, questions: list[EvaluationQuestion]) -> None:
    document_hits = 0
    keyword_hits = 0
    citation_hits = 0
    latencies: list[float] = []

    with httpx.Client(base_url=base_url.rstrip("/"), timeout=120.0) as client:
        for index, item in enumerate(questions, start=1):
            started = time.perf_counter()
            response = client.post(
                "/api/chat",
                json={
                    "conversation_id": None,
                    "question": item["question"],
                    "document_ids": [],
                    "top_k": 5,
                },
            )
            elapsed = time.perf_counter() - started
            response.raise_for_status()
            result = response.json()
            citations = result.get("citations", [])
            answer = str(result.get("answer", ""))

            document_hit = any(
                item["expected_document"].lower()
                in str(citation.get("document_title", "")).lower()
                for citation in citations
            )
            keyword_hit = item["expected_keyword"].lower() in answer.lower()
            citation_hit = bool(re.search(r"\[S\d+]", answer))

            document_hits += int(document_hit)
            keyword_hits += int(keyword_hit)
            citation_hits += int(citation_hit)
            latencies.append(elapsed)
            print(
                f"{index:02d}. document={document_hit} keyword={keyword_hit} "
                f"citation={citation_hit} latency={elapsed:.2f}s"
            )

    total = len(questions)
    print()
    print(f"Questions evaluated: {total}")
    print(f"Correct document retrieved: {document_hits}/{total}")
    print(f"Answers containing expected keyword: {keyword_hits}/{total}")
    print(f"Answers containing citations: {citation_hits}/{total}")
    print(f"Average latency: {mean(latencies):.2f} seconds")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the running RAG API.")
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path(__file__).with_name("evaluation_questions.example.json"),
    )
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()
    evaluate(args.api_url, load_questions(args.questions))


if __name__ == "__main__":
    main()
