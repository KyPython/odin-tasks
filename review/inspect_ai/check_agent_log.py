"""Audit native Inspect logs; score a real run, not a prerecorded calibration control."""
import argparse
import hashlib
import json
from pathlib import Path
from inspect_ai.log import read_eval_log

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    logs = sorted(args.log_dir.glob("*.eval"))
    if len(logs) != 1:
        raise SystemExit(f"Expected exactly one native Inspect agent log; found {len(logs)}")
    log = read_eval_log(str(logs[0]))
    model = str(log.eval.model)
    if "none/none" in model or not model.startswith("ollama/"):
        raise SystemExit(f"No authorized local model found: {model}")
    samples = log.samples or []
    if len(samples) != 3:
        raise SystemExit(f"Expected three real agent samples, got {len(samples)}")
    rows = []
    for item in samples:
        if not any(str(getattr(m, "role", "")) == "assistant" for m in (item.messages or [])):
            raise SystemExit("No model-generated assistant message for " + str(item.id))
        scores = item.scores or {}
        if "frozen_simulator_oracle" not in scores:
            raise SystemExit("Missing independent scorer for " + str(item.id))
        s = scores["frozen_simulator_oracle"]
        row = {"id": str(item.id), "score": str(s.value),
               "verdict": (s.metadata or {}).get("verdict", "UNKNOWN"),
               "reason": (s.metadata or {}).get("reason", str(s.reason or "UNKNOWN")),
               "model_usage_reported": bool(item.model_usage)}
        rows.append(row)
    data = {"kind": "real_local_model_agent_on_synthetic_simulator",
            "model": model,
            "tested_system": "native Inspect AI + Ollama on isolated GitHub runner",
            "scope": "three independent synthetic toy worlds; NO actual Odin task or external effect",
            "case_sha256": hashlib.sha256(Path(__file__).with_name("agent_cases.json").read_bytes()).hexdigest(),
            "log_filename": logs[0].name,
            "sample_count": len(rows),
            "samples": rows,
            "not_a_claim_of": ["human mastery", "paid Odin acceptance", "external real-world reliability", "general model ranking"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
