"""Run the starter test in two process-local timezones."""

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]
TIMEZONES = ("Pacific/Kiritimati", "Etc/GMT+12")


def run_in_timezone(timezone_name: str) -> int:
    environment = os.environ.copy()
    environment["TZ"] = timezone_name
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    return completed.returncode


def main() -> int:
    results = {timezone: run_in_timezone(timezone) for timezone in TIMEZONES}
    print("\nTimezone outcomes:")
    for timezone, returncode in results.items():
        print(f"  {timezone}: {'pass' if returncode == 0 else 'fail'}")

    if len(set(results.values())) == 1:
        print("The outcomes matched at this instant; inspect the displayed dates.")
    else:
        print("The same starter test produced different outcomes by timezone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
