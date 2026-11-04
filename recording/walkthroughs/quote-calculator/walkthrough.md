# Quote calculator — prepared repair and verification reference

This is an **AI-written, fully prepared reference** containing the completed analysis, exact tests, smallest production repair and planned narration. It is kept outside the captured project. It does not claim spontaneous or unaided discovery, personal authorship, external permission, a recording, submission or earned pay.

**Paid eligibility remains unresolved for a fully AI-written repair/test script.** The supplied Project Odin Writer Guidelines, physical page 63, directs the writer to know the software steps before recording. The document also discusses AI-prepared inputs and forbids AI interaction during capture. Those facts do not establish that this complete scripted solution is an eligible paid-task input. Reconcile the actual current task/platform requirements before monetized use; this reference does not invent an off-screen-analysis prohibition or grant approval. The source document inspected was `Project Odin Writer Guidelines.pdf`, SHA-256 `af751a041a8855eda3872b795b09f8c12a70c50679f38c47ee22750a9b4c0f81`.

## Exact task and source

- Task: `ODIN-5959D60FB16547A0A846BB836D8D0C3F`.
- Source: `https://github.com/KyPython/vacuous-test-suite-audit` at `c5986e93719cfd4b08a57104576c04a78d1f16ee`.
- Neutral workspace: `quote-calculator.code-workspace`; project `~/Desktop/TaskWork/quote-calculator/`.
- Approved Goal, unchanged: As a QA engineer, audit a synthetic Python module whose pytest suite passes even though a seeded defect breaks the documented behavior, identify the vacuous assertions that let it pass, rewrite them into meaningful checks, and verify that the strengthened suite fails on the defective build and passes on the corrected build.
- Goal SHA-256: `ad882a58279d4809c1a4c036554a3400509b50c46bbb58e41f9665d54a30b135`.
- Reviewed tools: Python **3.12.7**, pytest **8.3.5**; offline pytest installation comes from the existing kit.

Seven unchanged source files matched the pinned Git tree, manifest and Shared copy before preparation. The reference runner also checks the exact registry/manifest/Goal and preserves the input tree and wheel cache. The patches change only `tests/test_calculator.py` and `src/quote_calculator/calculator.py`; applying them to a disposable copy is separate from the unchanged starter.

## Prepared technical findings and observed evidence

`docs/behavior.md` requires tax on the discounted amount. The pinned implementation, `src/quote_calculator/calculator.py` line 42, instead calculates `tax = subtotal * tax_rate`. Its total then uses that same incorrect tax.

The original tests contain useful type/subtotal/input checks, but several assertions are too weak for this defect. Positive tax only proves nonzero tax. A positive discount plus `total < subtotal + tax` only proves some discount was subtracted. `total == subtotal - discount + tax` checks internal consistency with whatever tax was returned, rather than the correct tax amount. Two-decimal precision alone does not establish half-up rounding. These checks allow the seeded calculation error to stay green.

The expectations below come from the written contract, rather than copying the defective implementation:

| Case | Subtotal | Discount | Required tax | Required total | Observed defective tax / total |
| --- | ---: | ---: | ---: | ---: | --- |
| 8.00 × 9, tax 0.05 | 72.00 | 0.00 | 3.60 | 75.60 | 3.60 / 75.60 |
| 8.00 × 10, tax 0.05 | 80.00 | 8.00 | 3.60 | 75.60 | 4.00 / 76.00 |
| 20.00 × 12, tax 0.075 | 240.00 | 24.00 | 16.20 | 232.20 | 18.00 / 234.00 |
| 1.00 × 10, tax 1 | 10.00 | 1.00 | 9.00 | 18.00 | 10.00 / 19.00 |

For the ten-unit case, `(80.00 - 8.00) × 0.05 = 3.60`; total is `72.00 + 3.60 = 75.60`. For twelve units, `(240.00 - 24.00) × 0.075 = 16.20`; total is `216.00 + 16.20 = 232.20`.

The actual disposable verification recorded in `verification.json` observed **8 passed** before edits, **3 failed / 14 passed** after strengthening only the tests, **17 passed** with those same tests after the one-line repair, and **15 passed / 2 deselected** for the boundary subset. The three red cases are the ten-unit quote, the twelve-unit quote and the inclusive tax-rate-one quote. All fail on incorrect tax/total values. A repeat of the corrected example command produced identical bytes. Test timing varies; the results here are observed reference results, not a claim about a future recording.

## Off-screen preparation and reference files

Use the current assigned task and mandatory Recorder pre-record checklist. Keep external approval, current Studio fields/transition, real Recorder setup/permissions and paid eligibility separate from this technical reference. Preserve the exact Goal and input provenance. This preparation checked no human recording gate and never executed the Recorder helper or changed its workspace.

Keep this folder, patches, verification proof, Notion/GitHub material and all preparation tools off the captured display. `tests.patch` changes only the tests; `repair.patch` changes one production line; `solution.patch` combines both. They are reference/rehearsal files, not files already applied to the original starter. The on-camera route below identifies every planned edit and supports honest prepared narration.

Before capture, load `~/Desktop/TaskWork/quote-calculator.code-workspace` in the clean recording VS Code instance and `~/Desktop/TaskWork/quote-calculator-goal.txt` in a separate Goal window. Verify both User/workspace AI-disable settings, the selected task receipt and the current approved Goal. Keep the project open behind the Goal window. If any prerequisite or the eligibility of using a fully prepared code reference is unresolved, this document does not establish admission.

### Recording sequence — follow this order
**Step 1.** After the actual assigned-task checks and permitted-use requirements have passed, leave the Goal document behind TaskRecorder. Click **Start Recording**, minimize TaskRecorder, and say only the required opener: “I will be beginning my task soon. Here is the workflow I have in mind.” Keep the opener under 20 seconds. Minimize the Goal window with its yellow button, then choose the already-open `quote-calculator` project through VS Code’s **Window** menu.
**Step 2.** Once the project is forward, say: “This prepared plan uses a test-first check of the quote calculation.” Do not claim unaided discovery or personal authorship of the prepared analysis/tests. In Explorer, open `README.md`, then expand `docs` and open `behavior.md`. Show the documented discounted-tax formula and input rules. Choose **Terminal → New Terminal**; confirm the project directory with `pwd`, then record the original suite result:
```bash
pwd
.venv/bin/python -m pytest -q > baseline-tests.txt 2>&1
pytest_result=$?
cat baseline-tests.txt
printf 'Pytest exit: %s\n' "$pytest_result"
```
The prepared baseline observed **8 passed**, exit **0**. Narration: “These original tests are green. That establishes what they currently check; it does not establish every amount required by the behavior document.” If it is not the unchanged eight-test baseline, stop the planned edit sequence and inspect the actual starting state off-screen. Preserve an existing human attempt rather than resetting it.
**Step 3.** Open `tests/test_calculator.py`. Point to the positive-tax, positive-discount, total-consistency and cent-exponent assertions described above. Then expand `src → quote_calculator` and open `calculator.py`; point to the existing `tax = subtotal * tax_rate` line. Show the actual defective examples in the integrated terminal:
```bash
PYTHONPATH=src .venv/bin/python -c 'from decimal import Decimal; from quote_calculator import calculate_quote; print(calculate_quote(Decimal("8.00"), 10, Decimal("0.05"))); print(calculate_quote(Decimal("20.00"), 12, Decimal("0.075")))' > quote-before.txt
cat quote-before.txt
```
The prepared output is tax **4.00**, total **76.00** for ten units, and tax **18.00**, total **234.00** for twelve. Narration: “The documented rule gives 3.60 and 16.20 of tax in these cases. The old tests compare the total to the same tax returned by the implementation, so an internally consistent wrong tax can pass. This prepared plan uses exact contract-derived expectations to expose that gap.” Leave production unchanged for the red-test demonstration.
**Step 4.** Click `tests/test_calculator.py` in Explorer. Choose **Edit → Select All** in that editor and replace its contents with the exact prepared test file below. This is the complete planned test edit; its new expectations were prepared before this demonstration. Keep production untouched. The cases retain the original ordinary/input checks, replace weak amount assertions, and cover quantities 9/10, half-up rounding, invalid boolean/fractional quantities, inclusive tax-rate endpoints and zero price.
```python
from decimal import Decimal

import pytest

from quote_calculator import Quote, calculate_quote


def test_regular_quote_returns_itemized_amounts() -> None:
    quote = calculate_quote(Decimal("12.50"), 3, Decimal("0.08"))

    assert isinstance(quote, Quote)
    assert quote == Quote(
        subtotal=Decimal("37.50"),
        discount=Decimal("0.00"),
        tax=Decimal("3.00"),
        total=Decimal("40.50"),
    )


@pytest.mark.parametrize(
    ("quantity", "expected"),
    [
        (9, Quote(Decimal("72.00"), Decimal("0.00"), Decimal("3.60"), Decimal("75.60"))),
        (10, Quote(Decimal("80.00"), Decimal("8.00"), Decimal("3.60"), Decimal("75.60"))),
    ],
    ids=["below-threshold", "at-threshold"],
)
def test_volume_order_receives_discount(quantity: int, expected: Quote) -> None:
    assert calculate_quote(Decimal("8.00"), quantity, Decimal("0.05")) == expected


def test_tax_is_included_in_total() -> None:
    quote = calculate_quote(Decimal("20.00"), 12, Decimal("0.075"))

    assert quote == Quote(
        subtotal=Decimal("240.00"),
        discount=Decimal("24.00"),
        tax=Decimal("16.20"),
        total=Decimal("232.20"),
    )


@pytest.mark.parametrize(
    ("unit_price", "tax_rate", "expected"),
    [
        (Decimal("1.005"), Decimal("0.0825"),
         Quote(Decimal("1.01"), Decimal("0.00"), Decimal("0.08"), Decimal("1.09"))),
        (Decimal("0.10"), Decimal("0.05"),
         Quote(Decimal("0.10"), Decimal("0.00"), Decimal("0.01"), Decimal("0.11"))),
    ],
    ids=["subtotal-half-up", "tax-half-up"],
)
def test_amounts_have_cent_precision(unit_price: Decimal, tax_rate: Decimal, expected: Quote) -> None:
    quote = calculate_quote(unit_price, 1, tax_rate)

    assert quote == expected
    for amount in (quote.subtotal, quote.discount, quote.tax, quote.total):
        assert amount.as_tuple().exponent == -2


@pytest.mark.parametrize(
    ("unit_price", "quantity", "tax_rate"),
    [
        (Decimal("-0.01"), 1, Decimal("0.05")),
        (Decimal("1.00"), 0, Decimal("0.05")),
        (Decimal("1.00"), 1, Decimal("1.01")),
        (Decimal("1.00"), 1, Decimal("-0.01")),
        (Decimal("1.00"), True, Decimal("0.05")),
        (Decimal("1.00"), False, Decimal("0.05")),
        (Decimal("1.00"), 1.5, Decimal("0.05")),
        (Decimal("1.00"), -1, Decimal("0.05")),
    ],
    ids=["negative-price", "zero-quantity", "tax-above-one", "negative-tax",
         "true-quantity", "false-quantity", "fractional-quantity", "negative-quantity"],
)
def test_invalid_inputs_are_rejected(unit_price: Decimal, quantity: int, tax_rate: Decimal) -> None:
    with pytest.raises(ValueError):
        calculate_quote(unit_price, quantity, tax_rate)


@pytest.mark.parametrize(
    ("tax_rate", "expected"),
    [
        (Decimal("0"), Quote(Decimal("10.00"), Decimal("1.00"), Decimal("0.00"), Decimal("9.00"))),
        (Decimal("1"), Quote(Decimal("10.00"), Decimal("1.00"), Decimal("9.00"), Decimal("18.00"))),
    ],
    ids=["zero-rate", "one-rate"],
)
def test_tax_rate_endpoints_are_allowed(tax_rate: Decimal, expected: Quote) -> None:
    assert calculate_quote(Decimal("1.00"), 10, tax_rate) == expected


def test_zero_price_is_allowed() -> None:
    quote = calculate_quote(Decimal("0.00"), 10, Decimal("0.05"))

    assert quote == Quote(Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
```
Choose **File → Save All**. Narration: “These assertions compare all four returned amounts to values derived from the written contract. The original internal-consistency check could not detect this tax error. The boundary cases also protect the documented threshold, rounding and input rules.”
**Step 5.** With production still unchanged, record the strengthened-suite failure and preserve the test-file digest:
```bash
.venv/bin/python -m pytest -q > strengthened-before-repair.txt 2>&1
pytest_result=$?
cat strengthened-before-repair.txt
printf 'Pytest exit: %s\n' "$pytest_result"
shasum -a 256 tests/test_calculator.py > tests-before.sha256
cat tests-before.sha256
```
The prepared result is **3 failed, 14 passed**, exit **1**. The failures must be `test_volume_order_receives_discount[at-threshold]`, `test_tax_is_included_in_total` and `test_tax_rate_endpoints_are_allowed[one-rate]`; each reports differing `tax` and `total` values. Narration: “The stronger tests are now red on the defective calculation, for the expected amounts rather than an import or syntax problem. The other fourteen cases pass. This digest records the tests before the repair.” If an error is an unsaved edit or copying typo, compare this file with Step 4, correct that exact discrepancy, choose **File → Save All**, and rerun Step 5. If the three semantic failures are absent or other behavior fails, do not claim the intended negative control was demonstrated.
**Step 6.** In Explorer open `src → quote_calculator → calculator.py`. Replace only this tax expression, retaining its existing four-space indentation inside `calculate_quote`:
```python
tax = subtotal * tax_rate
```
with:
```python
tax = (subtotal - discount) * tax_rate
```
Leave the input validation, discount threshold/rate, `_money`, dataclass and total expression unchanged. Choose **File → Save All**. Narration: “The smallest correction changes the tax base to the discounted amount required by the document. The existing total expression can now use that corrected tax; rounding and unrelated validation remain in place.”
**Step 7.** Run the same strengthened suite, prove that its saved test file is unchanged, and run the documented boundary subset:
```bash
.venv/bin/python -m pytest -q > strengthened-after-repair.txt 2>&1
pytest_result=$?
cat strengthened-after-repair.txt
printf 'Pytest exit: %s\n' "$pytest_result"
shasum -a 256 tests/test_calculator.py > tests-after.sha256
cmp tests-before.sha256 tests-after.sha256
comparison_result=$?
printf 'Test digest comparison exit: %s\n' "$comparison_result"
.venv/bin/python -m pytest -q -k 'volume_order or amounts_have_cent_precision or invalid_inputs or tax_rate_endpoints or zero_price' > boundary-regressions.txt 2>&1
regression_result=$?
cat boundary-regressions.txt
printf 'Boundary regression exit: %s\n' "$regression_result"
```
The prepared full suite observed **17 passed**, exit **0**; the digest comparison returned **0**; the subset observed **15 passed, 2 deselected**, exit **0**. Narration: “The same tests that detected the defect now pass after the one-line repair. The unchanged digest rules out weakening them between red and green. The subset rechecks the volume boundary, rounding and valid/invalid input edges.” If the comparison fails, restore the exact saved Step 4 test text and revert only the Step 6 production line to `tax = subtotal * tax_rate`. Choose **File → Save All**, repeat Step 5 to re-establish the three tests-only failures, then repeat Steps 6 and 7; preserve the recording evidence instead of claiming an unchanged test set. For an unsaved production typo, correct the exact Step 6 line, **File → Save All**, then rerun Step 7. Stop advancement if a failure does not match either bounded correction.
**Step 8.** Produce and compare two corrected example outputs:
```bash
PYTHONPATH=src .venv/bin/python -c 'from decimal import Decimal; from quote_calculator import calculate_quote; print(calculate_quote(Decimal("8.00"), 10, Decimal("0.05"))); print(calculate_quote(Decimal("20.00"), 12, Decimal("0.075")))' > quote-after.txt
quote_first_result=$?
PYTHONPATH=src .venv/bin/python -c 'from decimal import Decimal; from quote_calculator import calculate_quote; print(calculate_quote(Decimal("8.00"), 10, Decimal("0.05"))); print(calculate_quote(Decimal("20.00"), 12, Decimal("0.075")))' > quote-repeat.txt
quote_repeat_result=$?
cat quote-after.txt
printf 'First generation exit: %s; repeat generation exit: %s\n' "$quote_first_result" "$quote_repeat_result"
if [ "$quote_first_result" -eq 0 ] && [ "$quote_repeat_result" -eq 0 ]; then
  cmp quote-after.txt quote-repeat.txt
  comparison_result=$?
  printf 'Quote output comparison exit: %s\n' "$comparison_result"
else
  printf '%s\n' 'HOLD: generation failed; comparison is not evidence.'
fi
```
The prepared corrected output shows ten-unit tax **3.60** / total **75.60**, and twelve-unit tax **16.20** / total **232.20**. Its two outputs matched, comparison exit **0**. Narration: “The displayed amounts now match the documented discounted-tax calculations. Identical repeated bytes show reproducibility for these inputs; the exact assertions establish correctness for the tested cases.” If either generation fails, do not use an empty-file comparison as success. Correct only a demonstrated command-copy typo, choose **File → Save All** if any file was edited, and rerun this entire step; otherwise stop before a completion claim.
**Step 9.** Only after those actual results have been observed, choose Explorer’s **New File**, name it `verification-note.md`, and record the result below, changing any number that differs from the actual recording rather than copying a false claim:
```markdown
# Quote calculation verification

This attempt follows a prepared test-first verification sequence.

The original suite passed 8 cases. Its positive-tax and internal-total checks
missed tax computed from the pre-discount subtotal.

Exact contract-derived amounts and documented boundary/input cases produced
3 failing and 14 passing cases before the production repair. The failures
identified incorrect discounted tax and total values.

The production repair changes the tax base to subtotal minus discount.
The same strengthened test file then passed all 17 cases; its before/after
digest comparison returned 0. The boundary subset passed 15 cases with 2
deselected. The repeated corrected quote outputs matched byte for byte.

For 8.00 x 10 at tax 0.05, tax is 3.60 and total is 75.60.
For 20.00 x 12 at tax 0.075, tax is 16.20 and total is 232.20.

Evidence: baseline-tests.txt, strengthened-before-repair.txt,
strengthened-after-repair.txt, boundary-regressions.txt,
tests-before.sha256, tests-after.sha256, quote-before.txt,
quote-after.txt and quote-repeat.txt.
```
Choose **File → Save All**. Open the saved note, corrected calculator, strengthened tests and evidence files from Explorer. Confirm that the promised deliverable is the corrected module plus the meaningful tests and actual red/green evidence; do not represent the reference rehearsal as this recording.
**Step 10.** Choose **File → Save All** once more. Bring TaskRecorder forward, click **Stop Recording**, and wait for **Stopping → Archiving → Idle**. Follow the existing assigned-task recording-QA and Studio submission checklist using only the actual video/archive/files from this attempt. Preserve the exact Goal and truthful input/preparation disclosure in the actual required metadata; never include this private reference folder or claim paid approval based on its technical PASS result.

## Reproduce off-screen in a disposable copy

Use the pinned public interpreter and existing read-only kit. The command creates a fresh private directory owned by the invoking account and preserves the installed reference proof:
```bash
proof_dir="$(mktemp -d /private/tmp/taskwork-quote-calculator-reference.XXXXXX)"
/usr/local/bin/python3 -I /Users/Shared/TaskWorkPlans/quote-calculator/rehearse.py \
  --inputs /Users/Shared/TaskWorkInputs \
  --runtime /Users/Shared/TaskWorkRuntime \
  --output "$proof_dir/proof.json"
```
In the cloud, the same script accepts the existing workflow’s source/runtime roots and uses `sys.executable`; it requires reviewed Python 3.12.7 and installs pytest 8.3.5 from `runtime/wheels` with network indexes disabled. It validates source/Goal pins, copies only the Quote starter to a system temporary directory, runs the weak baseline, applies `tests.patch`, verifies the exact semantic failures, applies `repair.patch`, runs the unchanged strengthened suite and boundary checks, compares repeated outputs, and checks that `solution.patch` produces the same final source files. All disposable copies are removed. Actual command/output records are in `verification.json`; source inputs, Goal, offline cache and Recorder workspace stay unchanged.

The proof records `sourceCommit`, `goalSha256`, actual `checks`, `sourceInputsUnchanged: true`, `recorderExecuted: false` and `recordingWorkspaceModified: false`. A PASS proves this prepared reference’s technical sequence on the pinned source and toolchain; it does not establish the human’s recording/admission or fully AI-written paid-task eligibility.
