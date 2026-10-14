"""Emit calibration-only report; never credit reference controls as agent wins."""
import argparse
import json
from pathlib import Path
from grader import load_cases, summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("calibration.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    for case in cases:
        if case.get("origin") != "synthetic_calibration" or case.get("calibration_expectation") not in ("PASS", "FAIL", "UNKNOWN", "HOLD"):
            raise SystemExit("Refuse to treat agent runs as calibration controls")
    result = summary(cases)
    for case, score in zip(cases, result["cases"]):
        if score["verdict"] != case["calibration_expectation"]:
            raise SystemExit("Grader calibration failure: " + case["case_id"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print("CALIBRATION PASS: no model run; " + str(result["counts"]))

if __name__ == "__main__":
    main()
