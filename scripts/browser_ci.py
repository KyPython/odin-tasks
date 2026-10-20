"""Native sandboxed Chrome controls using only self-contained loopback HTML."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    selected = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if not selected or not Path(selected).is_file() or not os.access(selected, os.X_OK):
        raise RuntimeError(
            "Explicit installed system Chrome executable is required; no download or no-sandbox fallback"
        )
    node = shutil.which("node")
    if not node:
        raise RuntimeError("The selected Node runtime is unavailable")
    artifacts = ROOT / "artifacts/browser"
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="synthetic-browser-home-") as temporary:
        env = {
            "PATH": str(Path(node).parent) + ":/usr/bin:/bin",
            "HOME": str(Path.home()),
            "XDG_CONFIG_HOME": str(Path(temporary) / "config"),
            "XDG_CACHE_HOME": str(Path(temporary) / "cache"),
            "TMPDIR": temporary,
            "LANG": "C.UTF-8",
            "PUPPETEER_EXECUTABLE_PATH": selected,
            "PUPPETEER_SKIP_DOWNLOAD": "true",
        }
        version = subprocess.check_output(
            [selected, "--version"], env=env, text=True
        ).strip()
        result = subprocess.run(
            [node, "--test", "test/audit.test.cjs"],
            cwd=ROOT / "accessibility",
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
        )
        (artifacts / "stdout.txt").write_text(result.stdout)
        (artifacts / "stderr.txt").write_text(result.stderr)
        report = {
            "passed": result.returncode == 0,
            "exit_code": result.returncode,
            "browser": version,
            "browser_executable": selected,
            "node": subprocess.check_output(
                [node, "--version"], env=env, text=True
            ).strip(),
            "scope": "self-contained synthetic loopback HTML only",
            "browser_sandbox_disabled": False,
            "application_audit_verified": False,
            "network_boundary": "native runner; fixtures contain no external resource URLs",
        }
        (artifacts / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
