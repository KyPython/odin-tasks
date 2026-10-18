"""Actual offline QA/dispatch/promptfoo suite; enter through run_offline.py."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

from network_probe import probe

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "qa"), str(ROOT / "dispatch")]


def source_hashes() -> dict[str, str]:
    paths = [
        ROOT / name
        for name in ("requirements.in", "requirements.lock", "pytest.ini", "Dockerfile")
    ]
    for directory in ("qa", "dispatch", "tests", "scripts"):
        paths.extend(
            path
            for path in (ROOT / directory).rglob("*")
            if path.is_file() and path.suffix in (".py", ".json", ".yaml")
        )
    paths.extend(
        [
            ROOT / "tools/promptfoo/package.json",
            ROOT / "tools/promptfoo/package-lock.json",
        ]
    )
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def check_network() -> dict:
    if os.environ.get("EVAL_NETWORK_POSITIVE_VERIFIED") != "1":
        raise RuntimeError(
            "An actual positive listener control is required; use scripts/run_offline.py"
        )
    host = os.environ.get("EVAL_NETWORK_CONTROL_HOST")
    if not host:
        raise RuntimeError("Missing numeric network-control address")
    socket.inet_aton(host)
    interfaces = [name for _, name in socket.if_nameindex()]
    if interfaces != ["lo"]:
        raise RuntimeError("Expected Docker --network none with only loopback")
    return {
        "kind": "Docker --network none",
        "interfaces": interfaces,
        "negative": probe(host, blocked=True),
        "outside_connection_verified": True,
    }


def run(argv: list[str], name: str, artifacts: Path) -> int:
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=240)
    (artifacts / f"{name}.stdout.txt").write_text(result.stdout)
    (artifacts / f"{name}.stderr.txt").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(
            f"{name} failed with exit {result.returncode}; see synthetic artifacts"
        )
    return result.returncode


def check_metrics() -> dict:
    from document_qa import load_responses
    from qa_metrics import score_cases
    from dispatch_metrics import OfflineJudge, score_required_tool_names
    from dispatch_schema import (
        recompute_enforcement,
        required_delivery,
        synthetic_controls,
    )

    qa_runs = [score_cases(load_responses()) for _ in range(3)]
    if (
        qa_runs[0] != qa_runs[1]
        or qa_runs[0] != qa_runs[2]
        or not all(row["passed"] for row in qa_runs[0])
    ):
        raise RuntimeError(
            "Actual DeepEval QA fixture replays did not pass identically"
        )
    judge = OfflineJudge()
    controls = []
    for record in synthetic_controls():
        actual = {
            "enforcement_pass": recompute_enforcement(record)["pass"],
            "required_delivery_score": required_delivery(record)["score"],
            "required_delivery_applicable": required_delivery(record)["applicable"],
            "required_tool_score": score_required_tool_names(record, judge)["score"],
            "executed_count": sum(
                call["outcome"]["status"] in ("succeeded", "failed")
                for call in record["calls"]
            ),
            "blocked_count": len(record["blocked"]),
        }
        if actual != record["expected_assertions"]:
            raise RuntimeError(
                f"Synthetic dispatch control disagreed: {record['record_id']}"
            )
        controls.append(
            {
                "id": record["record_id"],
                "expected": record["expected_assertions"],
                "actual": actual,
            }
        )
    if judge.generation_calls:
        raise RuntimeError("A deterministic metric attempted judge inference")
    return {
        "kind": "synthetic controls only; no real benchmark records",
        "qa": {"cases": qa_runs[0], "repeats": 3, "repeat_results_equal": True},
        "dispatch": controls,
        "judge_calls": 0,
        "live_service_verified": False,
    }


def main() -> int:
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    initial_hashes = source_hashes()
    network = check_network()
    versions = {
        name: importlib.metadata.version(name) for name in ("deepeval", "pytest")
    }
    if versions != {"deepeval": "4.3.0", "pytest": "8.4.2"}:
        raise RuntimeError(
            "Installed evaluation packages differ from the locked contract"
        )
    run(
        [sys.executable, "-m", "pytest", "--junitxml=artifacts/pytest.xml"],
        "pytest",
        artifacts,
    )
    metrics = check_metrics()
    (artifacts / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n"
    )
    cli = ROOT / "tools/promptfoo/node_modules/.bin/promptfoo"
    version = subprocess.check_output(
        [str(cli), "--version"], cwd=ROOT, text=True
    ).strip()
    if version != "0.124.1":
        raise RuntimeError("Installed promptfoo differs from the lock")
    versions["promptfoo"] = version
    versions["node"] = subprocess.check_output(["node", "--version"], text=True).strip()
    run(
        [
            str(cli),
            "eval",
            "--config",
            "qa/promptfooconfig.yaml",
            "--output",
            "artifacts/promptfoo.json",
            "--no-cache",
            "--no-progress-bar",
        ],
        "promptfoo",
        artifacts,
    )
    stats = json.loads((artifacts / "promptfoo.json").read_text())["results"]["stats"]
    if not (
        stats.get("successes") == 4
        and stats.get("failures") == 0
        and stats.get("errors") == 0
        and stats.get("tokenUsage", {}).get("total") == 0
    ):
        raise RuntimeError(
            "Actual promptfoo fixture outcomes differ from four successes/zero errors/zero model tokens"
        )
    if source_hashes() != initial_hashes:
        raise RuntimeError("Maintained sources changed during verification")
    report = {
        "passed": True,
        "runtime": versions,
        "source_hashes": initial_hashes,
        "network": network,
        "promptfoo_stats": stats,
        "local_promptfoo_provider_invocations": 4,
        "remote_model_requests": 0,
        "synthetic_dispatch_controls": len(metrics["dispatch"]),
        "qa_cases": 4,
        "qa_repeats": 3,
        "live_service_verified": False,
        "limitations": [
            "Only invented fixture facts and scripted dispatch controls are included.",
            "No real private dispatch records, live product/model quality, tenant identity or ingestion were evaluated.",
            "QA exact-match grammar is not a general semantic-quality judge.",
        ],
    }
    (artifacts / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed": True,
                "report": "artifacts/summary.json",
                "remote_model_requests": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"Offline CI failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
