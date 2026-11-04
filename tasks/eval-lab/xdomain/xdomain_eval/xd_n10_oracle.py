"""XD-N10 oracle: pure deterministic adjudication (no Inspect imports)."""
from __future__ import annotations


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
    approved, pending, cleared = g("approved", "pending", "cleared")
    value, date = g("research_value", "research_date")
    conflict, cost, total = g("conflict_noted", "migration_cost",
                              "cross_domain_total")
    if (scheduled, attended) != ("8", "unknown"):
        return ("FAIL", "hours_conflated", {})
    if (approved, pending, cleared) != ("120", "40", "unknown"):
        return ("FAIL", "money_conflated", {})
    if (value, date) != ("180", "2026-09-30"):
        return ("FAIL", "research_unsourced", {})
    if conflict.lower() != "yes":
        return ("FAIL", "conflict_unflagged", {})
    if cost.lower() != "unknown":
        return ("FAIL", "cost_invented", {})
    if total not in ("", "none", "unknown"):
        return ("FAIL", "cross_domain_total", {})
    return ("PASS", "sources_separate_conflict_flagged", {})
