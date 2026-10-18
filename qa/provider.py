"""Promptfoo adapter: saved synthetic responses by default, HTTP only by opt-in."""

from __future__ import annotations

import json
import os
from urllib import error, parse, request

from document_qa import get_case, load_responses, parse_json, validate_response

MAX_RESPONSE_BYTES = 1024 * 1024


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Query redirects are not accepted")


def live_settings() -> tuple[str, dict[str, str]]:
    if os.environ.get("DOCUMENT_QA_LIVE") != "1":
        raise ValueError("Live query requests require DOCUMENT_QA_LIVE=1")
    if os.environ.get("DOCUMENT_QA_CORPUS_READY") != "1":
        raise ValueError(
            "Declare a separately prepared matching corpus/namespace before live evaluation"
        )
    endpoint = os.environ.get("DOCUMENT_QA_URL", "")
    parsed = parse.urlsplit(endpoint)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError(
            "Supply an explicit HTTP(S) query endpoint without embedded credentials"
        )
    if parsed.path.rstrip("/") != "/query" or parsed.query:
        raise ValueError("The endpoint must end in /query without query parameters")
    if parsed.scheme == "http" and parsed.hostname not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        raise ValueError("Use HTTPS for a non-loopback query endpoint")
    headers = {"Content-Type": "application/json"}
    auth = os.environ.get("DOCUMENT_QA_AUTH")
    if auth == "api-key":
        key = os.environ.get("DOCUMENT_QA_API_KEY")
        if not key:
            raise ValueError(
                "API-key mode requires DOCUMENT_QA_API_KEY; anonymous fallback is disabled"
            )
        headers["X-API-Key"] = key
    elif auth != "anonymous":
        raise ValueError("Explicitly select DOCUMENT_QA_AUTH=anonymous or api-key")
    return endpoint.rstrip("/") + "?mode=answer&cacheMode=off", headers


def query_service(query: str) -> dict:
    endpoint, headers = live_settings()
    payload = {
        "query": query,
        "topK": 5,
        "retrievalMode": "auto",
        "includeMemory": False,
        "memoryTopK": 0,
    }
    req = request.Request(
        endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    # Do not inherit proxy settings or follow a redirect with an API-key header.
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=30) as response:
            if response.status != 200:
                raise ValueError("Query service returned an unsuccessful HTTP status")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (error.URLError, OSError):
        raise ValueError(
            "Query transport failed; response bodies and credentials are omitted"
        ) from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Query response exceeds the configured limit")
    try:
        result = parse_json(raw.decode("utf-8"))
        validate_response(result, query)
        return result
    except (ValueError, UnicodeError, TypeError):
        raise ValueError("Query response does not match the answer contract") from None


def call_api(prompt, options, context):
    case_id = context.get("vars", {}).get("case_id")
    case = get_case(case_id)
    if prompt.strip() != case["question"]:
        raise ValueError("Rendered prompt must match the declared synthetic question")
    mode = options.get("config", {}).get("mode", "fixture")
    if mode == "fixture":
        response = load_responses()[case_id]
        validate_response(response, case["question"])
        return {
            "output": json.dumps(response, ensure_ascii=False),
            "tokenUsage": {"total": 0},
            "cost": 0,
            "metadata": {
                "transport": "saved-synthetic-fixture",
                "localProviderInvocations": 1,
                "remoteRequests": 0,
                "liveServiceVerified": False,
            },
        }
    if mode != "live":
        raise ValueError("Choose fixture or live adapter mode")
    response = query_service(case["question"])
    return {
        "output": json.dumps(response, ensure_ascii=False),
        "metadata": {
            "transport": "explicit-live-http",
            "localProviderInvocations": 1,
            "remoteRequests": 1,
            "authAndNamespaceVerified": False,
            "serverModelRequests": "unmeasured",
        },
    }
