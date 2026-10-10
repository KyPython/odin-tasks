### Recording sequence — follow this order
**Step 1.** After the internal Bootcamp runbook's **Before practice — Recorder checks** passes for this actual attempt, leave `callback-state.code-workspace` open in the clean recording VS Code instance and show its exact candidate Goal in the separate Goal window. Bring TaskRecorder forward, click **Start Recording**, then minimize TaskRecorder. Say this supplied practice opener in under **20 seconds**: “I'm beginning guided local practice on this synthetic callback handler. I'll check the unchanged behavior, add the prepared tests, apply the planned validation, and verify the saved local results.” Minimize the Goal window with its yellow button and use VS Code's **Window** menu to bring the already-open `callback-state.code-workspace` project forward. This is guided internal candidate practice, with no Odin approval, Studio assignment or unaided-transfer claim.
**Step 2.** Use **Go → Go to File…** (**⌘P**) to open `README.md`, then `callback.py`, `fixtures.py`, `run_fixtures.py` and `tests/test_callback.py`. Explain the prepared analysis: “The written contract requires state binding, expiration checks and rejection of reuse. The starter only checks for a code, removes the pending request, and returns success. Its ordinary tests cover the valid return path and code-free output, so passing them does not establish those rejection paths.” Use **Terminal → New Terminal** and run each command individually:
```bash
cd "$HOME/Desktop/TaskWork/callback-state"
pwd
/usr/local/bin/python3 --version
/usr/local/bin/python3 -B -m unittest discover -s tests -v
echo $?
/usr/local/bin/python3 -B run_fixtures.py
echo $?
```
The pinned disposable starter used Python **3.12.7**, passed **2 tests** with exit **0**, and the harness exited **0** while incorrectly accepting `missing`, `mismatched` and `expired` as `ok`. In `replayed`, it returned `ok` twice: first `/dashboard`, then `/`. State/code values were absent from the JSON. If actually displayed, say: “The existing success path works, but these deterministic negative fixtures are accepted. I'll add the prepared assertions before changing the handler.” If the version, source, test count or observations differ, state the actual difference, stop capture normally and preserve the attempt for off-screen setup/source reconciliation.
**Step 3.** Use **File → New Text File** (**⌘N**), then **File → Save As…** (**⇧⌘S**) to create `~/Desktop/TaskWork/callback-state/tests/test_state_validation.py`. Manually enter this complete prepared test file; keep the existing `tests/test_callback.py` unchanged:
```python
"""Decisive local callback-state checks for the prepared practice plan."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from callback import CallbackResult, handle_callback  # noqa: E402
from fixtures import FIXED_NOW, SYNTHETIC_CODE, EXPECTED_STATE, scenario  # noqa: E402
from run_fixtures import run  # noqa: E402


class CallbackStateTests(unittest.TestCase):
    def assert_error(self, result: CallbackResult, category: str) -> None:
        self.assertEqual(result, CallbackResult(status="error", category=category))

    def test_missing_empty_and_non_string_state_are_rejected(self) -> None:
        for label, state in (("absent", None), ("empty", ""), ("non-string", 7)):
            with self.subTest(case=label):
                case = scenario("valid")
                if label == "absent":
                    case["query"].pop("state")
                else:
                    case["query"]["state"] = state
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "missing_state")
                self.assertIn("oauth_request", case["session"])

    def test_mismatch_and_unbound_state_are_rejected(self) -> None:
        for label in ("mismatch", "unbound", "unicode-mismatch"):
            with self.subTest(case=label):
                case = scenario("mismatched")
                if label == "unbound":
                    case["session"] = {}
                elif label == "unicode-mismatch":
                    case["query"]["state"] = "different-opaque-state-\u00e9"
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "state_mismatch")
                if label != "unbound":
                    self.assertIn("oauth_request", case["session"])
                    valid_query = scenario("valid")["query"]
                    retry = handle_callback(valid_query, case["session"], FIXED_NOW)
                    self.assertEqual(retry, CallbackResult(status="ok", redirect_to="/dashboard"))

    def test_expired_state_is_rejected_without_consuming_request(self) -> None:
        case = scenario("expired")
        result = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assert_error(result, "state_expired")
        self.assertIn("oauth_request", case["session"])

    def test_expiration_deadline_and_one_second_before(self) -> None:
        for label, remaining in (("at-deadline", 0), ("one-second-before", 1)):
            with self.subTest(case=label):
                case = scenario("valid")
                case["session"]["oauth_request"]["expires_at"] = FIXED_NOW + remaining
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                if remaining == 0:
                    self.assert_error(result, "state_expired")
                    self.assertIn("oauth_request", case["session"])
                else:
                    self.assertEqual(result, CallbackResult(status="ok", redirect_to="/dashboard"))
                    self.assertNotIn("oauth_request", case["session"])

    def test_replay_is_rejected_after_one_success(self) -> None:
        case = scenario("replayed")
        first = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assertEqual(first, CallbackResult(status="ok", redirect_to="/dashboard"))
        self.assertNotIn("oauth_request", case["session"])
        second = handle_callback(case["query"], case["session"], FIXED_NOW)
        third = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assert_error(second, "state_replayed")
        self.assert_error(third, "state_replayed")

    def test_missing_code_behavior_is_preserved(self) -> None:
        case = scenario("valid")
        case["query"].pop("code")
        result = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assert_error(result, "missing_code")
        self.assertIn("oauth_request", case["session"])

    def test_malformed_pending_records_fail_closed(self) -> None:
        pending_cases = (
            ("none", None),
            ("empty-record", {}),
            ("non-record", ["invalid"]),
            ("non-string-state", {"state": 7}),
            ("empty-state", {"state": ""}),
        )
        for label, pending in pending_cases:
            with self.subTest(case=label):
                case = scenario("valid")
                case["session"]["oauth_request"] = pending
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "state_mismatch")

    def test_invalid_expiration_values_fail_closed(self) -> None:
        for label, expires_at in (("missing", None), ("string", "future"), ("boolean", True)):
            with self.subTest(case=label):
                case = scenario("valid")
                case["session"]["oauth_request"]["expires_at"] = expires_at
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "state_expired")
                self.assertIn("oauth_request", case["session"])

    def test_default_success_return_path_is_preserved(self) -> None:
        case = scenario("valid")
        case["session"]["oauth_request"].pop("return_to")
        result = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assertEqual(result, CallbackResult(status="ok", redirect_to="/"))
        self.assertNotIn("oauth_request", case["session"])

    def test_exact_serialized_scenarios_are_stable_and_credential_free(self) -> None:
        ok = {"status": "ok", "category": None, "redirect_to": "/dashboard"}
        def error(category: str) -> dict[str, str | None]:
            return {"status": "error", "category": category, "redirect_to": None}
        expected = {
            "valid": [ok],
            "missing": [error("missing_state")],
            "mismatched": [error("state_mismatch")],
            "expired": [error("state_expired")],
            "replayed": [ok, error("state_replayed")],
        }
        first = run()
        second = run()
        self.assertEqual(first, expected)
        first_json = json.dumps(first, indent=2, sort_keys=True)
        self.assertEqual(first_json, json.dumps(second, indent=2, sort_keys=True))
        sensitive_values = (
            SYNTHETIC_CODE,
            EXPECTED_STATE,
            scenario("mismatched")["query"]["state"],
        )
        for index, value in enumerate(sensitive_values):
            with self.subTest(sensitive_value_index=index):
                self.assertTrue(value not in first_json, "serialized output contains a sensitive fixture value")


if __name__ == "__main__":
    unittest.main()
```
Use **File → Save All** (**⌥⌘S**). Say: “These checks preserve the success and missing-code paths, reject absent or unbound state, define expiration at the deadline, and exercise repeated use of the same session. They also require the exact five fixture results and ensure serialized results omit the synthetic sensitive values.” The explicit prepared boundary is **now greater than or equal to expires_at is expired**; malformed expiration values also fail closed. This is a documented local technical choice, not evidence of a provider's policy.
**Step 4.** Return to the existing integrated terminal and run the strengthened suite before repairing the handler:
```bash
/usr/local/bin/python3 -B -m unittest discover -s tests -v
echo $?
```
The verified tests-only phase ran **12 tests**, exited **1**, and reported **FAILED (failures=17, errors=1)** because subtests cover several invalid inputs. The ordinary success, default return path and missing-code checks still passed. Required failures included missing/mismatched/unbound state, expiration and replay; the malformed list-valued pending record also raised an `AttributeError` in the starter. If observed, say: “The new assertions expose the missing validation while the preserved ordinary paths still pass. The handler needs to validate before consuming the pending request.” If the suite reports a syntax/import error, compare the saved file/path with the complete file above and Save All before retrying. If all checks already pass, stop and preserve the attempt; do not claim a fail-before result or overwrite an already changed starter.
**Step 5.** Use **⌘P** to open `callback.py`. Replace its content with this complete reviewed implementation:
```python
"""Synthetic OAuth callback boundary used by the bootcamp exercise."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hmac import compare_digest
from typing import Any, MutableMapping


@dataclass(frozen=True)
class CallbackResult:
    status: str
    category: str | None = None
    redirect_to: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        """Return a JSON-friendly response without callback credentials."""
        return asdict(self)


def handle_callback(
    query: dict[str, str],
    session: MutableMapping[str, Any],
    now: int,
) -> CallbackResult:
    """Validate this local callback before consuming its pending request."""
    if "code" not in query:
        return CallbackResult(status="error", category="missing_code")

    state = query.get("state")
    if not isinstance(state, str) or not state:
        return CallbackResult(status="error", category="missing_state")

    pending = session.get("oauth_request")
    if not isinstance(pending, dict):
        used_state = session.get("oauth_used_state")
        if isinstance(used_state, str) and compare_digest(
            state.encode("utf-8"), used_state.encode("utf-8")
        ):
            return CallbackResult(status="error", category="state_replayed")
        return CallbackResult(status="error", category="state_mismatch")

    expected_state = pending.get("state")
    if not isinstance(expected_state, str) or not expected_state or not compare_digest(
        state.encode("utf-8"), expected_state.encode("utf-8")
    ):
        return CallbackResult(status="error", category="state_mismatch")

    expires_at = pending.get("expires_at")
    if type(expires_at) is not int or now >= expires_at:
        return CallbackResult(status="error", category="state_expired")

    redirect_to = pending.get("return_to", "/")
    session.pop("oauth_request")
    session["oauth_used_state"] = expected_state
    return CallbackResult(status="ok", redirect_to=redirect_to)
```
Use **File → Save All** (**⌥⌘S**). Say: “A nonempty string state must match the pending record before anything is consumed. The UTF-8 byte comparison also handles opaque non-ASCII values. Expiration uses the injected timestamp. Only a successful callback removes the pending request and stores a session-local used-state marker, which rejects reuse of that same consumed request. The result contains only status, category and redirect.” The used-state marker stays in the local mutable session; it is never placed in the response or logs. This exercise does not establish atomic or persistent production session handling.
**Step 6.** In the existing terminal, run the complete suite twice, saving all edited files before every check or retry:
```bash
/usr/local/bin/python3 -B -m unittest discover -s tests -v
echo $?
/usr/local/bin/python3 -B -m unittest discover -s tests -v
echo $?
```
The repaired disposable reference reported **Ran 12 tests**, **OK**, and exit **0** both times; an independent fresh copy with the combined patch also passed all **12**. If actually observed, say: “All twelve tests pass, including the five required outcomes, the deadline boundary, malformed records, preservation of rejected pending requests, and credential-free serialization. The valid path still redirects to dashboard, and a missing return path still uses slash.” If anything differs, use the recovery actions below instead of narrating the reference result as this attempt's outcome.
**Step 7.** Use **File → Save All**. Create and inspect actual verification outputs inside this attempt with this terminal block:
```bash
(
  set -e
  mkdir -p practice-checks
  /usr/local/bin/python3 -B run_fixtures.py > practice-checks/callback-run-1.json
  /usr/local/bin/python3 -B run_fixtures.py > practice-checks/callback-run-2.json
  cat practice-checks/callback-run-1.json
  /usr/bin/cmp practice-checks/callback-run-1.json practice-checks/callback-run-2.json
  printf 'Repeated callback outputs are byte-identical.\n'
)
echo $?
```
The reference group produced these exact result categories: `valid` → `ok` with `/dashboard`; `missing` → `missing_state`; `mismatched` → `state_mismatch`; `expired` → `state_expired`; and `replayed` → first `ok` with `/dashboard`, then `state_replayed`. Each error has `status: error` and `redirect_to: null`. `cmp` produced no output and exited **0**. Confirm the actual saved data semantically and check that no synthetic code/state value appears by running:
```bash
/usr/local/bin/python3 -B - <<'PYCHECK'
import json
from pathlib import Path
from fixtures import SCENARIOS
path = Path("practice-checks/callback-run-1.json")
text = path.read_text()
observed = json.loads(text)
ok = {"status": "ok", "category": None, "redirect_to": "/dashboard"}
def error(category):
    return {"status": "error", "category": category, "redirect_to": None}
expected = {"valid": [ok], "missing": [error("missing_state")], "mismatched": [error("state_mismatch")], "expired": [error("state_expired")], "replayed": [ok, error("state_replayed")]}
assert observed == expected, "fixture results differ from the local contract"
for case in SCENARIOS.values():
    for field in ("code", "state"):
        value = case["query"].get(field)
        assert not value or value not in text, "serialized output contains a sensitive fixture value"
assert path.read_bytes() == Path("practice-checks/callback-run-2.json").read_bytes()
print("Exact fixture results and sensitive-value checks passed.")
PYCHECK
echo $?
```
The prepared assertion printed **Exact fixture results and sensitive-value checks passed.** and exited **0**. If the block or assertion fails, report that actual failure and follow the concrete recovery branch; do not treat byte-identical data alone as correct rejection. The JSON files are generated during this practice attempt, not supplied completed outputs. If all results actually match, say: “The saved fixture outputs are identical and contain the exact required outcomes without callback secrets. These are deterministic local results only; no provider interaction or production session-storage guarantee was tested.”
**Step 8.** Use **File → Save All** and inspect `callback.py`, both test files and `practice-checks/callback-run-1.json` in **⌘P**. Summarize only this attempt's actual observed changes/results, including any failure/retry. Bring TaskRecorder forward from the Dock, click **Stop Recording**, and wait for **Stopping → Archiving → Idle**. Preserve the real workspace and archive, then review the recording through the internal Bootcamp runbook. Report guided-practice evidence truthfully; actual practice success, unaided skill transfer, external approval and payment remain separate, unverified human/evidence decisions.
**Deterministic recovery actions — preserve the attempt**
- Wrong directory: run `pwd`, then `cd "$HOME/Desktop/TaskWork/callback-state"`; keep the existing terminal and workspace.
- Test import/syntax error: use **⌘P** to confirm the new file is exactly `tests/test_state_validation.py` and compare its imports/indentation with the complete file in Step 3. Save All before repeating the suite.
- Tests-only phase unexpectedly green: stop capture, preserve the actual source and archive, and reconcile whether the selected starter was already changed; do not reset it or invent the red phase.
- Missing/mismatch/replay assertions still fail after repair: compare the complete `callback.py` in Step 5, including validation before `session.pop`, the exact category strings, and the `oauth_used_state` marker. Save All and rerun all twelve tests; keep the assertions intact.
- Expiration tests fail: check `type(expires_at) is not int or now >= expires_at`; do not use wall-clock time or alter the fixed fixtures.
- JSON comparison fails: inspect both saved files and confirm the original harness/fixtures stayed unchanged. Save All and rerun Step 7 after the full suite passes; preserve the earlier failure in the actual recording evidence.
- Serialized sensitive-value assertion fails: stop capture normally and preserve the attempt. Do not paste query/session values into notes, weaken the assertion or claim provider security.
- Unexpected interpreter/source/setup problem: stop TaskRecorder and wait through Stopping → Archiving → Idle, preserve all work, and reconcile off-screen. Never rerun batch setup over edited attempts.
- Every retry after an edit starts with **File → Save All**; a later passing retry does not erase an earlier observed failure.
