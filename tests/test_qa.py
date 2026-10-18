"""Synthetic QA oracle, mock adapter and actual DeepEval metric controls."""

import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
from urllib.error import HTTPError
import pytest
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
import qa_metrics as qa
import document_qa as oracle
import assertion
import provider
import test_cases


@pytest.fixture
def responses():
    return oracle.load_responses()


@pytest.mark.parametrize("case_id", ["retention", "backup", "combined", "insufficient"])
def test_saved_synthetic_cases_use_real_deepeval_metrics(responses, case_id):
    response = responses[case_id]
    case = oracle.get_case(case_id)
    for dimension in qa.DIMENSIONS:
        if dimension == "insufficient_evidence" and case["evidence"]:
            continue
        metric = qa.DocumentQAMetric(case_id, dimension)
        assert isinstance(metric, BaseMetric)
        test_case = LLMTestCase(
            input=case["question"], actual_output=json.dumps(response)
        )
        assert metric.measure(test_case) == 1
        assert metric.is_successful()
        assert asyncio.run(metric.a_measure(test_case)) == 1
        assert metric.model is None
        assert metric.evaluation_cost == 0


@pytest.mark.parametrize(
    "answer",
    [
        "The Aster archive retains audit records for 22 days. [p0]",
        "The Aster archive does not retain audit records for 21 days. [p0]",
        "The Aster archive retains audit records for 21 days and uses AES-256. [p0]",
        "I don’t have enough information in the provided documents to answer that.",
    ],
)
def test_wrong_negated_added_or_unjustifiably_refused_answer_fails(responses, answer):
    response = responses["retention"]
    response["data"]["answer"] = answer
    result = oracle.score_response("retention", response)
    assert not result["passed"]
    assert result["dimensions"]["exact_answer"]["score"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "wrong_index",
        "extra_inline",
        "wrong_source",
        "wrong_text",
        "extra_metadata",
        "duplicate_index",
        "empty_text",
        "nan_score",
        "boolean_index",
        "wrong_query",
        "missing_data",
    ],
)
def test_citation_or_envelope_corruption_cannot_pass(responses, mutation):
    response = responses["retention"]
    data = response["data"]
    if mutation == "missing":
        data["citations"] = []
    elif mutation == "wrong_index":
        data["citations"][0]["index"] = 3
    elif mutation == "extra_inline":
        data["answer"] += " [p7]"
    elif mutation == "wrong_source":
        data["citations"][0]["metadata"]["source"] = "synthetic/fabricated.md"
    elif mutation == "wrong_text":
        data["citations"][0]["text"] = "A forged passage says 21 days."
    elif mutation == "extra_metadata":
        extra = deepcopy(responses["backup"]["data"]["citations"][0])
        extra["index"] = 1
        data["citations"].append(extra)
    elif mutation == "duplicate_index":
        data["citations"].append(deepcopy(data["citations"][0]))
    elif mutation == "empty_text":
        data["citations"][0]["text"] = ""
    elif mutation == "nan_score":
        data["citations"][0]["score"] = float("nan")
    elif mutation == "boolean_index":
        data["citations"][0]["index"] = True
    elif mutation == "wrong_query":
        data["query"] = "a different request"
    else:
        response.pop("data")
    try:
        result = oracle.score_response("retention", response)
    except ValueError:
        return
    assert not result["passed"]
    assert not result["dimensions"]["citation_support"]["passed"]


def test_unsupported_answer_needs_abstention_not_a_plausible_fact(responses):
    response = responses["insufficient"]
    response["data"]["answer"] = "The Aster archive uses AES-256."
    result = oracle.score_response("insufficient", response)
    assert result["dimensions"]["exact_answer"]["score"] == 0
    assert result["dimensions"]["insufficient_evidence"]["score"] == 0


def test_abstention_can_retain_true_retrieval_metadata(responses):
    response = responses["insufficient"]
    response["data"]["answer"] = oracle.ABSTENTIONS[2]
    response["data"]["citations"] = responses["retention"]["data"]["citations"]
    assert oracle.score_response("insufficient", response)["passed"]
    response["data"]["citations"][0]["text"] = "Invented evidence."
    assert not oracle.score_response("insufficient", response)["passed"]


def test_inline_citations_cannot_be_swapped_between_facts(responses):
    response = responses["combined"]
    response["data"][
        "answer"
    ] = "The Aster archive retains audit records for 21 days. [p1] The Aster archive creates a backup every 8 hours. [p0]"
    result = oracle.score_response("combined", response)
    assert result["dimensions"]["exact_answer"]["passed"]
    assert not result["dimensions"]["citation_support"]["passed"]


def test_promptfoo_fixture_provider_never_touches_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A fixture tried to make an HTTP request")

    monkeypatch.setattr(provider, "query_service", forbidden)
    for case in test_cases.generate_tests():
        variables = case["vars"]
        result = provider.call_api(
            variables["question"], {"config": {"mode": "fixture"}}, {"vars": variables}
        )
        assert result["metadata"]["remoteRequests"] == 0
        assert result["metadata"]["localProviderInvocations"] == 1
        assert result["tokenUsage"]["total"] == 0
        assert assertion.get_assert(result["output"], {"vars": variables})["pass"]


def test_promptfoo_assertion_rejects_malformed_response():
    assert not assertion.get_assert(
        '{"answer":"21 days"}', {"vars": {"case_id": "retention"}}
    )["pass"]


@pytest.mark.parametrize("request_id", [None, "", "   ", 17])
def test_service_request_id_is_required(responses, request_id):
    response = responses["retention"]
    response["requestId"] = request_id
    with pytest.raises(ValueError, match="requestId"):
        oracle.score_response("retention", response)


@pytest.fixture
def live_env(monkeypatch):
    for name in (
        "DOCUMENT_QA_LIVE",
        "DOCUMENT_QA_URL",
        "DOCUMENT_QA_CORPUS_READY",
        "DOCUMENT_QA_AUTH",
        "DOCUMENT_QA_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DOCUMENT_QA_LIVE", "1")
    monkeypatch.setenv("DOCUMENT_QA_URL", "http://127.0.0.1:3000/query")
    monkeypatch.setenv("DOCUMENT_QA_CORPUS_READY", "1")
    monkeypatch.setenv("DOCUMENT_QA_AUTH", "anonymous")


@pytest.mark.parametrize(
    "missing",
    [
        "DOCUMENT_QA_LIVE",
        "DOCUMENT_QA_URL",
        "DOCUMENT_QA_CORPUS_READY",
        "DOCUMENT_QA_AUTH",
    ],
)
def test_live_opt_in_prerequisites_are_checked_before_transport(
    live_env, monkeypatch, missing
):
    monkeypatch.delenv(missing)
    monkeypatch.setattr(
        provider.request,
        "build_opener",
        lambda *args: pytest.fail("Unopted live call touched HTTP transport"),
    )
    with pytest.raises(ValueError):
        provider.query_service(oracle.get_case("retention")["question"])


def test_api_key_mode_has_no_anonymous_fallback(live_env, monkeypatch):
    monkeypatch.setenv("DOCUMENT_QA_AUTH", "api-key")
    with pytest.raises(ValueError, match="anonymous fallback"):
        provider.live_settings()


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://remote.example/query",
        "https://user:password@example.test/query",
        "https://example.test/query?mode=retrieval",
        "https://example.test/ingest",
    ],
)
def test_invalid_live_endpoints_are_rejected(live_env, monkeypatch, endpoint):
    monkeypatch.setenv("DOCUMENT_QA_URL", endpoint)
    with pytest.raises(ValueError):
        provider.live_settings()


def test_opted_mock_http_uses_actual_contract_and_preserves_citations(
    live_env, monkeypatch, responses
):
    expected = responses["combined"]
    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return json.dumps(expected).encode()

    def open_request(req, timeout):
        captured.update(url=req.full_url, body=json.loads(req.data), timeout=timeout)
        return Response()

    monkeypatch.setattr(
        provider.request,
        "build_opener",
        lambda *handlers: SimpleNamespace(open=open_request),
    )
    assert provider.query_service(expected["data"]["query"]) == expected
    assert captured["url"] == "http://127.0.0.1:3000/query?mode=answer&cacheMode=off"
    assert captured["body"] == {
        "query": expected["data"]["query"],
        "topK": 5,
        "retrievalMode": "auto",
        "includeMemory": False,
        "memoryTopK": 0,
    }
    assert captured["timeout"] == 30


def test_http_errors_do_not_expose_response_or_key(live_env, monkeypatch):
    def fail(req, timeout):
        raise HTTPError(req.full_url, 401, "synthetic-secret-error-payload", {}, None)

    monkeypatch.setattr(
        provider.request, "build_opener", lambda *args: SimpleNamespace(open=fail)
    )
    with pytest.raises(ValueError, match="Query transport failed") as error:
        provider.query_service(oracle.get_case("retention")["question"])
    assert "synthetic-secret" not in str(error.value)


def test_redirect_is_not_followed():
    with pytest.raises(ValueError, match="redirect"):
        provider.NoRedirect().redirect_request(
            None, None, 302, "", {}, "https://elsewhere.example/query"
        )
