"""Failure artifacts from the real CI command wrapper; no providers or Docker."""

import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.fixture
def ci(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("fixture_ci", scripts / "ci.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failed_command_retains_both_output_streams(ci, tmp_path):
    command = [
        sys.executable,
        "-I",
        "-S",
        "-c",
        "import sys; print('fixture output'); "
        "print('fixture failure', file=sys.stderr); sys.exit(7)",
    ]
    with pytest.raises(RuntimeError, match="exit 7"):
        ci.run(command, "negative", tmp_path)
    assert (tmp_path / "negative.stdout.txt").read_text() == "fixture output\n"
    assert (tmp_path / "negative.stderr.txt").read_text() == "fixture failure\n"


def test_timed_out_command_retains_partial_output(ci, tmp_path, monkeypatch):
    original_run = ci.subprocess.run

    def bounded_fixture_run(*args, **kwargs):
        kwargs["timeout"] = 1
        return original_run(*args, **kwargs)

    monkeypatch.setattr(ci.subprocess, "run", bounded_fixture_run)
    command = [
        sys.executable,
        "-I",
        "-S",
        "-c",
        "import sys,time; print('fixture started', flush=True); "
        "print('fixture diagnostic', file=sys.stderr, flush=True); time.sleep(30)",
    ]
    with pytest.raises(RuntimeError, match="timed out"):
        ci.run(command, "timeout", tmp_path)
    assert (tmp_path / "timeout.stdout.txt").read_text() == "fixture started\n"
    assert (tmp_path / "timeout.stderr.txt").read_text() == "fixture diagnostic\n"
