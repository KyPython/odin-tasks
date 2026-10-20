#!/usr/bin/env python3
"""Run disposable Docker probes and a network-none evaluation container."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


def command(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(argv, text=True, capture_output=True, timeout=360)
    if check and result.returncode:
        raise RuntimeError(f"Docker operation failed: {result.stderr.strip()[:1000]}")
    return result


def main(args: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="evaluation-lab-ci:local")
    parser.add_argument("--output-dir", type=Path, required=True)
    options = parser.parse_args(args)
    output = options.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    listener = "eval-probe-" + uuid.uuid4().hex[:12]
    suite = "eval-suite-" + uuid.uuid4().hex[:12]
    basic = ["docker"]
    try:
        command(
            [
                *basic,
                "run",
                "--detach",
                "--name",
                listener,
                "--pull",
                "never",
                "--network",
                "bridge",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--entrypoint",
                "python",
                options.image,
                "scripts/network_probe.py",
                "serve",
            ]
        )
        address = command(
            [
                *basic,
                "inspect",
                "--format",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                listener,
            ]
        ).stdout.strip()
        probe_command = [
            *basic,
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "bridge",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--entrypoint",
            "python",
            options.image,
            "scripts/network_probe.py",
            "connect",
            "--host",
            address,
        ]
        positive = None
        for _ in range(10):
            result = command(probe_command, check=False)
            if result.returncode == 0:
                positive = json.loads(result.stdout)
                break
            time.sleep(0.2)
        if not positive or not positive.get("connected"):
            raise RuntimeError(
                "A real numeric-address positive network control did not pass"
            )
        result = command(
            [
                *basic,
                "run",
                "--name",
                suite,
                "--pull",
                "never",
                "--network",
                "none",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--env",
                "EVAL_NETWORK_POSITIVE_VERIFIED=1",
                "--env",
                f"EVAL_NETWORK_CONTROL_HOST={address}",
                options.image,
            ],
            check=False,
        )
        (output / "stdout.txt").write_text(result.stdout)
        (output / "stderr.txt").write_text(result.stderr)
        copied = command(
            [*basic, "cp", f"{suite}:/workspace/artifacts/.", str(output)], check=False
        )
        positive_after = command(probe_command, check=False)
        if positive_after.returncode:
            raise RuntimeError(
                "The positive listener was unavailable after the negative control"
            )
        evidence = {
            "positive_before": positive,
            "positive_after": json.loads(positive_after.stdout),
            "same_numeric_address": address,
            "runtime_network": "none",
            "container_exit_code": result.returncode,
            "artifacts_copied": copied.returncode == 0,
            "image": options.image,
        }
        (output / "network-control.json").write_text(
            json.dumps(evidence, indent=2) + "\n"
        )
        print(
            json.dumps(
                {
                    "passed": result.returncode == 0 and copied.returncode == 0,
                    "report_directory": str(output),
                    "container_exit_code": result.returncode,
                }
            )
        )
        return result.returncode or (0 if copied.returncode == 0 else 1)
    finally:
        # Only unique containers created by this invocation are removed.
        command([*basic, "rm", "--force", suite, listener], check=False)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Offline runner failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
