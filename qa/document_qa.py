"""Shared exact-fixture oracle. No model, application or evaluator dependencies."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any

PROJECT = Path(__file__).resolve().parent
REFERENCE = re.compile(r"\[p(\d+)\]")
ABSTENTIONS = (
    "I don’t have enough information in the provided documents to answer that.",
    "The provided context does not contain enough information to answer this question.",
    "The retrieved evidence is too weak to provide a reliable answer. Please refine the query or ingest more domain-specific documents.",
)


def normalized(text: str) -> str:
    return " ".join(text.replace("’", "'").casefold().split())


def parse_json(text: str) -> Any:
    def invalid_constant(value: str) -> None:
        raise ValueError(f"Nonfinite JSON constant: {value}")

    return json.loads(text, parse_constant=invalid_constant)


def load_suite() -> tuple[dict[str, dict], dict[str, dict]]:
    corpus = parse_json((PROJECT / "corpus.json").read_text())
    cases = parse_json((PROJECT / "cases.json").read_text())
    for source, key in ((corpus, "documents"), (cases, "cases")):
        if source.get("schema_version") != 1 or source.get("synthetic") is not True:
            raise ValueError("This oracle requires version 1 synthetic fixtures")
        if not isinstance(source.get(key), list) or not source[key]:
            raise ValueError(f"Missing {key}")
    documents = {item["id"]: item for item in corpus["documents"]}
    questions = {item["id"]: item for item in cases["cases"]}
    if len(documents) != len(corpus["documents"]) or len(questions) != len(
        cases["cases"]
    ):
        raise ValueError("Duplicate synthetic fixture IDs")
    if len({doc["source"] for doc in documents.values()}) != len(documents):
        raise ValueError("Duplicate synthetic source identifiers")
    for doc in documents.values():
        if any(
            not isinstance(doc.get(key), str) or not doc[key].strip()
            for key in ("id", "source", "text")
        ):
            raise ValueError("Malformed synthetic document")
    for case in questions.values():
        if not isinstance(case.get("question"), str) or not case["question"].strip():
            raise ValueError("Missing synthetic question")
        evidence = case.get("evidence")
        if not isinstance(evidence, list) or len(evidence) != len(set(evidence)):
            raise ValueError("Malformed synthetic evidence mapping")
        if any(item not in documents for item in evidence):
            raise ValueError("Case references an unknown synthetic document")
    return documents, questions


def get_case(case_id: str) -> dict:
    _, cases = load_suite()
    if case_id not in cases:
        raise ValueError("Unknown synthetic case ID")
    return cases[case_id]


def load_responses(path: Path | None = None) -> dict[str, dict]:
    value = parse_json((path or PROJECT / "saved-responses.json").read_text())
    if value.get("schema_version") != 1 or not isinstance(value.get("responses"), dict):
        raise ValueError("Expected version 1 saved response mapping")
    _, cases = load_suite()
    if set(value["responses"]) != set(cases):
        raise ValueError("Saved responses must contain exactly the declared cases")
    return value["responses"]


def validate_response(value: Any, query: str) -> dict:
    """Validate the service's actual {requestId, data} answer envelope."""
    if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
        raise ValueError("Expected a service response with a data object")
    if not isinstance(value.get("requestId"), str) or not value["requestId"].strip():
        raise ValueError("Missing response requestId")
    data = value["data"]
    if data.get("query") != query:
        raise ValueError("Response query does not match this case")
    if not isinstance(data.get("answer"), str) or not data["answer"].strip():
        raise ValueError("Missing answer text")
    if not isinstance(data.get("citations"), list):
        raise ValueError("Missing citations array")
    indices = set()
    for citation in data["citations"]:
        if not isinstance(citation, dict):
            raise ValueError("Malformed citation")
        index = citation.get("index")
        if type(index) is not int or index < 0 or index in indices:
            raise ValueError("Citation indices must be unique nonnegative integers")
        indices.add(index)
        if not isinstance(citation.get("text"), str) or not citation["text"].strip():
            raise ValueError("Missing citation text")
        score = citation.get("score")
        if type(score) not in (float, int) or not math.isfinite(score):
            raise ValueError("Citation score must be finite")
        if not isinstance(citation.get("metadata"), dict) or not isinstance(
            citation["metadata"].get("source"), str
        ):
            raise ValueError("Missing citation source metadata")
    return data


def score_response(case_id: str, response: Any) -> dict[str, Any]:
    documents, _ = load_suite()
    case = get_case(case_id)
    if isinstance(response, str):
        response = parse_json(response)
    data = validate_response(response, case["question"])
    answer = data["answer"]
    references = {int(index) for index in REFERENCE.findall(answer)}
    plain_answer = normalized(REFERENCE.sub("", answer))
    unsupported = not case["evidence"]
    accepted_abstention = normalized(answer) in {
        normalized(text) for text in ABSTENTIONS
    }
    expected_answer = normalized(
        " ".join(documents[item]["text"] for item in case["evidence"])
    )
    answer_ok = accepted_abstention if unsupported else plain_answer == expected_answer

    by_source = {doc["source"]: doc for doc in documents.values()}
    cited_documents = []
    index_by_document = {}
    citation_ok = True
    for citation in data["citations"]:
        document = by_source.get(citation["metadata"]["source"])
        if document is None or normalized(citation["text"]) != normalized(
            document["text"]
        ):
            citation_ok = False
        elif document["id"] in cited_documents:
            citation_ok = False
        else:
            cited_documents.append(document["id"])
            index_by_document[document["id"]] = citation["index"]
    indices = {citation["index"] for citation in data["citations"]}
    if unsupported:
        # Production may retain retrieval metadata after replacing an answer.
        citation_ok = citation_ok and not references
    else:
        citation_ok = (
            citation_ok
            and references == indices
            and set(cited_documents) == set(case["evidence"])
        )
        if citation_ok:
            expected_layout = " ".join(
                f"{documents[item]['text']} [p{index_by_document[item]}]"
                for item in case["evidence"]
            )

            def layout(text):
                return normalized(
                    REFERENCE.sub(lambda match: f" {match.group()} ", text)
                )

            citation_ok = layout(answer) == layout(expected_layout)
    dimensions = {
        "exact_answer": {
            "applicable": True,
            "score": float(answer_ok),
            "passed": answer_ok,
            "reason": "Exact normalized synthetic facts or accepted product abstention; paraphrases are not scored semantically.",
        },
        "citation_support": {
            "applicable": True,
            "score": float(citation_ok),
            "passed": citation_ok,
            "reason": "Inline indices and exact synthetic source/text support; valid retrieval metadata may remain on abstention.",
        },
        "insufficient_evidence": {
            "applicable": unsupported,
            "score": float(accepted_abstention) if unsupported else None,
            "passed": accepted_abstention if unsupported else None,
            "reason": "Accepted explicit abstention required for the unsupported synthetic question; N/A otherwise.",
        },
    }
    return {
        "case_id": case_id,
        "synthetic": True,
        "passed": all(
            item["passed"] for item in dimensions.values() if item["applicable"]
        ),
        "dimensions": dimensions,
    }
