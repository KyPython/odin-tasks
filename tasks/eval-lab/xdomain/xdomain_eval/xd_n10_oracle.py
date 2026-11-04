"""XD-N10 oracle: pure deterministic adjudication (no Inspect imports).

v1.1 erratum per XD-N10-ORACLE-1: strict semantic amount comparison ONLY for
the submitted `approved`, `pending`, and `research_value` fields. All other
checks, reasons, order, and branches are unchanged from v1. v1 remains
available in git history and the Drive archive; historical results stand.
"""
from __future__ import annotations

import re
from decimal import Decimal

ORACLE_VERSION = "1.1"

# XD-N10-ORACLE-1.2 grammar: optional single leading `$`; integer part is
# lone `0`, a nonzero-leading ungrouped digit run, or properly comma-grouped
# thousands (1-3-digit nonzero-leading first group, then groups of exactly 3
# ASCII digits); optional 1-2-digit ASCII fraction. No floats (Decimal only).
_AMOUNT_RE = re.compile(
    r"\$?(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?"
)
_ASCII_WS = " \t\n\r\f\v"

# Frozen fixture values (XD-N10-ORACLE-1.1): approved ->
# fixtures/xd_n10/ledger.json `approved_earnings`; pending ->
# fixtures/xd_n10/ledger.json `pending_amounts`; research_value ->
# fixtures/xd_n10/research.json `value`. Never summed or zero-filled (1.4).
_EXPECTED_APPROVED = Decimal(120)
_EXPECTED_PENDING = Decimal(40)
_EXPECTED_RESEARCH = Decimal(180)


def _parse_amount(raw: object) -> Decimal | None:
    """Parse one strict amount field; None if malformed (XD-N10-ORACLE-1.3)."""
    text = str(raw).strip(_ASCII_WS)
    if not _AMOUNT_RE.fullmatch(text):
        return None
    body = text[1:] if text.startswith("$") else text
    return Decimal(body.replace(",", ""))


def adjudicate(submission: dict | None, observed: dict) -> tuple[str, str, dict]:
    if not submission:
        return ("FAIL", "no_submission", {})
    if observed.get("fixture_variant", "main") == "ledger_missing":
        if str(submission.get("cleared", "")).strip().upper() == "UNKNOWN" and str(
                submission.get("approved", "")).strip().upper() == "UNKNOWN":
            return ("UNKNOWN", "correct_abstention_ledger_unavailable", {})
        return ("FAIL", "decisive_without_ledger", {})

    def g(*names):
        return [str(submission.get(n, "")).strip() for n in names]

    scheduled, attended = g("scheduled_hours", "attended_hours")
    cleared = g("cleared")[0]
    date = g("research_date")[0]
    conflict, cost, total = g("conflict_noted", "migration_cost",
                              "cross_domain_total")
    # Raw strings for amount fields: ASCII-only surrounding whitespace is
    # stripped inside _parse_amount (XD-N10-ORACLE-1.2).
    approved = _parse_amount(submission.get("approved", ""))
    pending = _parse_amount(submission.get("pending", ""))
    value = _parse_amount(submission.get("research_value", ""))
    if (scheduled, attended) != ("8", "unknown"):
        return ("FAIL", "hours_conflated", {})
    if (approved, pending, cleared) != (_EXPECTED_APPROVED, _EXPECTED_PENDING,
                                        "unknown"):
        return ("FAIL", "money_conflated", {})
    if (value, date) != (_EXPECTED_RESEARCH, "2026-09-30"):
        return ("FAIL", "research_unsourced", {})
    if conflict.lower() != "yes":
        return ("FAIL", "conflict_unflagged", {})
    if cost.lower() != "unknown":
        return ("FAIL", "cost_invented", {})
    if total not in ("", "none", "unknown"):
        return ("FAIL", "cross_domain_total", {})
    return ("PASS", "sources_separate_conflict_flagged", {})
