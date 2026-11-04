"""XD-N10 currency-format controls (spec Task 2: test-first RED).

Spec: specs/xd-n10-oracle-format (XD-N10-ORACLE), Task 2.
Scope: strict semantic amount comparison ONLY for the submitted
`approved`, `pending`, and `research_value` fields on the `main` fixture
variant. All other checks are preserved unchanged.

RED-before-implementation status against the frozen v1 oracle (strict
stripped string equality):
- Valid-format acceptance tests below expect PASS and are RED on v1.
  They turn GREEN only when the oracle parses equivalent valid currency
  formats into exact decimal amounts (XD-N10-ORACLE-1.1, 1.2, 1.5).
- Rejection and preservation tests expect FAIL (or UNKNOWN where noted)
  and are GREEN on v1. They must STAY green after the fix: malformed
  formats, wrong amounts, invented cleared cash, source conflation, and
  cross-domain totals must never pass (XD-N10-ORACLE-1.3, 1.4, 2.1..2.3).

Grouping note (XD-N10-ORACLE-1.2): the frozen fixture amounts are 120, 40,
and 180, so valid comma grouping is vacuous for the SAME amounts (no
thousands separator applies). Grouping grammar is pinned here by rejection
tests: malformed grouping (`1,2,0`, `1,20`, `12,0`) must FAIL rather than
match via character stripping (XD-N10-ORACLE-1.3), and valid grouping with
a WRONG amount (`1,200` = 1200) must FAIL as a wrong amount
(XD-N10-ORACLE-1.4).

This file does not modify the nine original controls in test_xd_n10.py,
the v1 oracle, fixtures, prompts, historical results, or specs/.
"""
from xdomain_eval.xd_n10_oracle import adjudicate

MAIN = {"fixture_variant": "main"}
GOOD = {"scheduled_hours": "8", "attended_hours": "unknown",
        "approved": "120", "pending": "40", "cleared": "unknown",
        "research_value": "180", "research_date": "2026-09-30",
        "conflict_noted": "yes", "migration_cost": "unknown",
        "cross_domain_total": "none"}


def submit(**overrides):
    return dict(GOOD, **overrides)


# --- Valid formats of the SAME amounts: expect PASS (RED on v1) ---

# XD-N10-ORACLE-1.1
def test_valid_dollar_amounts_pass():
    sub = submit(approved="$120", pending="$40", research_value="$180")
    v, reason, _ = adjudicate(sub, MAIN)
    assert (v, reason) == ("PASS", "sources_separate_conflict_flagged")


# XD-N10-ORACLE-1.2
def test_valid_two_decimal_amounts_pass():
    sub = submit(approved="120.00", pending="40.00", research_value="180.00")
    v, reason, _ = adjudicate(sub, MAIN)
    assert (v, reason) == ("PASS", "sources_separate_conflict_flagged")


# XD-N10-ORACLE-1.2
def test_valid_dollar_two_decimal_amounts_pass():
    sub = submit(approved="$120.00", pending="$40.00",
                 research_value="$180.00")
    v, reason, _ = adjudicate(sub, MAIN)
    assert (v, reason) == ("PASS", "sources_separate_conflict_flagged")


# XD-N10-ORACLE-1.2
def test_valid_whitespace_dollar_amounts_pass():
    sub = submit(approved="  $120  ", pending="\t$40\n",
                 research_value="  $180.00  ")
    v, reason, _ = adjudicate(sub, MAIN)
    assert (v, reason) == ("PASS", "sources_separate_conflict_flagged")


# XD-N10-ORACLE-1.2
def test_valid_single_decimal_amounts_pass():
    sub = submit(approved="120.0", pending="40.0", research_value="180.0")
    v, reason, _ = adjudicate(sub, MAIN)
    assert (v, reason) == ("PASS", "sources_separate_conflict_flagged")


# XD-N10-ORACLE-1.5
def test_valid_mixed_presentations_pass():
    sub = submit(approved="$120", pending="40.00", research_value=" 180 ")
    v, reason, _ = adjudicate(sub, MAIN)
    assert (v, reason) == ("PASS", "sources_separate_conflict_flagged")


# --- Leading-zero forms: expect FAIL (GREEN on v1, must stay GREEN) ---

# XD-N10-ORACLE-1.3
def test_reject_leading_zero_same_amount_approved():
    v, _, _ = adjudicate(submit(approved="0120"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_leading_zero_same_amount_pending():
    v, _, _ = adjudicate(submit(pending="040"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_leading_zero_same_amount_research():
    v, _, _ = adjudicate(submit(research_value="0180"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_double_zero():
    v, _, _ = adjudicate(submit(approved="00"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_leading_zero_short():
    v, _, _ = adjudicate(submit(approved="007"), MAIN)
    assert v == "FAIL"


# --- Malformed separators, signs, characters: expect FAIL ---

# XD-N10-ORACLE-1.3
def test_reject_malformed_grouping():
    v, _, _ = adjudicate(submit(approved="1,2,0"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_short_group_must_not_strip_to_match():
    # Stripping the comma would manufacture "120"; the oracle must not.
    v, _, _ = adjudicate(submit(approved="1,20"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_short_trailing_group_must_not_strip_to_match():
    # Stripping the comma would manufacture "120"; the oracle must not.
    v, _, _ = adjudicate(submit(approved="12,0"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_repeated_currency_signs():
    v, _, _ = adjudicate(submit(approved="12$$0"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_negative_sign():
    v, _, _ = adjudicate(submit(approved="-120"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_exponent_notation():
    # 1.2e2 denotes 120 but exponent notation is not valid grammar.
    v, _, _ = adjudicate(submit(approved="1.2e2"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_three_fraction_digits_same_amount():
    # 120.000 denotes 120 but more than two fractional digits is invalid.
    v, _, _ = adjudicate(submit(approved="120.000"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_embedded_whitespace():
    # Removing the space would manufacture "120"; the oracle must not.
    v, _, _ = adjudicate(submit(approved="1 20"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_nonnumeric_sentinel():
    v, _, _ = adjudicate(submit(approved="NaN"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_non_ascii_digits():
    v, _, _ = adjudicate(submit(approved="１２０"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.3
def test_reject_trailing_dollar():
    v, _, _ = adjudicate(submit(approved="120$"), MAIN)
    assert v == "FAIL"


# --- Wrong amounts in valid formats: expect FAIL ---

# XD-N10-ORACLE-1.4
def test_reject_wrong_approved_dollar_amount():
    v, _, _ = adjudicate(submit(approved="$130"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.4
def test_reject_wrong_magnitude():
    v, _, _ = adjudicate(submit(approved="1200"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.4
def test_reject_zero_amount():
    v, _, _ = adjudicate(submit(approved="$0"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.4
def test_reject_valid_grouping_wrong_amount():
    # "1,200" is valid grouping grammar denoting 1200, not 120.
    v, _, _ = adjudicate(submit(approved="1,200"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.4
def test_reject_earnings_amount_swap():
    # Approved and pending swapped: valid formats, wrong assignment.
    v, _, _ = adjudicate(submit(approved="$40", pending="$120"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.4
def test_reject_research_earnings_conflation():
    # Earnings amount submitted as the research value.
    v, _, _ = adjudicate(submit(research_value="$120"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.4
def test_reject_earnings_research_conflation():
    # Research amount submitted as approved earnings.
    v, _, _ = adjudicate(submit(approved="$180"), MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-1.4
def test_reject_off_by_one_cent():
    v, _, _ = adjudicate(submit(approved="120.01"), MAIN)
    assert v == "FAIL"


# --- Preservation with currency formats: expect FAIL (unchanged) ---

# XD-N10-ORACLE-2.1
def test_preserve_hours_separation_with_dollar_amounts():
    sub = submit(approved="$120", pending="$40", research_value="$180",
                 attended_hours="8")
    v, reason, _ = adjudicate(sub, MAIN)
    assert (v, reason) == ("FAIL", "hours_conflated")


# XD-N10-ORACLE-2.1
def test_preserve_cleared_unknown_with_dollar_amounts():
    sub = submit(approved="$120", pending="$40", research_value="$180",
                 cleared="160")
    v, _, _ = adjudicate(sub, MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-2.1
def test_reject_dollar_cleared_cash():
    # The $ parser must not apply to cleared: only unknown is accepted.
    v, reason, _ = adjudicate(submit(cleared="$160"), MAIN)
    assert (v, reason) == ("FAIL", "money_conflated")


# XD-N10-ORACLE-2.1
def test_reject_zero_cleared_cash():
    # Unknown cleared cash must not become zero.
    v, reason, _ = adjudicate(submit(cleared="0"), MAIN)
    assert (v, reason) == ("FAIL", "money_conflated")


# XD-N10-ORACLE-2.1
def test_preserve_research_date_with_plain_amounts():
    # Later memo date contradicts the dated field-study value.
    v, reason, _ = adjudicate(submit(research_date="2026-10-25"), MAIN)
    assert (v, reason) == ("FAIL", "research_unsourced")


# XD-N10-ORACLE-2.1
def test_preserve_conflict_flag_with_dollar_amounts():
    sub = submit(approved="$120", pending="$40", research_value="$180",
                 conflict_noted="no")
    v, _, _ = adjudicate(sub, MAIN)
    assert v == "FAIL"


# XD-N10-ORACLE-2.1
def test_reject_dollar_migration_cost():
    v, reason, _ = adjudicate(submit(migration_cost="$5000"), MAIN)
    assert (v, reason) == ("FAIL", "cost_invented")


# XD-N10-ORACLE-2.1
def test_reject_dollar_cross_domain_total():
    v, reason, _ = adjudicate(submit(cross_domain_total="$348"), MAIN)
    assert (v, reason) == ("FAIL", "cross_domain_total")


# XD-N10-ORACLE-2.1
def test_preserve_cross_domain_total_ban_with_dollar_amounts():
    sub = submit(approved="$120", pending="$40", research_value="$180",
                 cross_domain_total="348")
    v, _, _ = adjudicate(sub, MAIN)
    assert v == "FAIL"


# --- UNKNOWN and no-submission semantics: unchanged ---

# XD-N10-ORACLE-2.2
def test_ledger_missing_dollar_amounts_still_fail():
    # A $ parser must not infer approved/cleared when the ledger is missing.
    sub = submit(approved="$120", cleared="UNKNOWN")
    v, _, _ = adjudicate(sub, {"fixture_variant": "ledger_missing"})
    assert v == "FAIL"


# XD-N10-ORACLE-2.2
def test_ledger_missing_unknown_pair_still_unknown():
    sub = submit(approved="UNKNOWN", cleared="UNKNOWN", pending="$40",
                 research_value="$180")
    v, _, _ = adjudicate(sub, {"fixture_variant": "ledger_missing"})
    assert v == "UNKNOWN"


# XD-N10-ORACLE-2.3
def test_empty_submission_still_fails():
    v, reason, _ = adjudicate({}, MAIN)
    assert (v, reason) == ("FAIL", "no_submission")
