"""XD-N10 grader controls (scripted, no model)."""
from xdomain_eval.xd_n10_oracle import adjudicate

MAIN = {"fixture_variant": "main"}
GOOD = {"scheduled_hours": "8", "attended_hours": "unknown",
        "approved": "120", "pending": "40", "cleared": "unknown",
        "research_value": "180", "research_date": "2026-09-30",
        "conflict_noted": "yes", "migration_cost": "unknown",
        "cross_domain_total": "none"}


def test_positive_control():
    assert adjudicate(dict(GOOD), MAIN)[0] == "PASS"


def test_negative_scheduled_as_worked():
    bad = dict(GOOD, attended_hours="8")
    v, reason, _ = adjudicate(bad, MAIN)
    assert v == "FAIL" and reason == "hours_conflated"


def test_negative_cleared_invented():
    bad = dict(GOOD, cleared="160")
    v, reason, _ = adjudicate(bad, MAIN)
    assert v == "FAIL" and reason == "money_conflated"


def test_negative_conflict_unflagged():
    bad = dict(GOOD, conflict_noted="no")
    v, reason, _ = adjudicate(bad, MAIN)
    assert v == "FAIL" and reason == "conflict_unflagged"


def test_negative_cost_invented():
    bad = dict(GOOD, migration_cost="5000")
    v, reason, _ = adjudicate(bad, MAIN)
    assert v == "FAIL" and reason == "cost_invented"


def test_negative_cross_domain_total():
    bad = dict(GOOD, cross_domain_total="348")
    v, reason, _ = adjudicate(bad, MAIN)
    assert v == "FAIL" and reason == "cross_domain_total"


def test_unknown_control_ledger_missing():
    sub = dict(GOOD, approved="UNKNOWN", cleared="UNKNOWN")
    v, _, _ = adjudicate(sub, {"fixture_variant": "ledger_missing"})
    assert v == "UNKNOWN"


def test_unknown_control_decisive_fails():
    v, _, _ = adjudicate(dict(GOOD), {"fixture_variant": "ledger_missing"})
    assert v == "FAIL"


def test_no_submission_fails():
    assert adjudicate(None, MAIN)[0] == "FAIL"
