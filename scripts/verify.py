"""Run the verification checks for an implemented project phase."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def verify(root: Path, phase: int) -> int:
    backend = root / "backend"
    frontend = root / "frontend"
    npm_name = "npm.cmd" if os.name == "nt" else "npm"
    npm = shutil.which(npm_name) or npm_name
    if phase == 0:
        pytest_args = ["tests/test_health.py", "tests/test_scenario_schema.py"]
    elif phase == 1:
        pytest_args = ["--hypothesis-show-statistics", "--ignore=tests/test_social.py",
                       "--ignore=tests/test_observation.py"]
    else:
        pytest_args = ["--hypothesis-show-statistics"]
    checks = [
        ("Backend import", [sys.executable, "-c", "import agentverse.api.main"], backend),
        ("Backend tests", [sys.executable, "-m", "pytest", "-q", *pytest_args], backend),
        ("Frontend type check", [npm, "--offline", "run", "typecheck"], frontend),
        ("Frontend build", [npm, "--offline", "run", "build"], frontend),
    ]

    if phase >= 5:
        checks.append(("Paired offline demo", [sys.executable, str(root / "scripts/demo.py"),
                      "--mode", "rule_based", "--seed", "42", "--scenario", "food-scarcity"], root))
    failed = False
    for label, command, directory in checks:
        print(f"\n{label}", flush=True)
        try:
            result = subprocess.run(command, cwd=directory, check=False)
            exit_code = result.returncode
        except OSError as error:
            print(error, file=sys.stderr, flush=True)
            exit_code = 1
        print(f"{label} exit code {exit_code}", flush=True)
        failed |= exit_code != 0
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=[0, 1, 2, 3, 4, 5], required=True)
    args = parser.parse_args()
    return verify(Path(__file__).resolve().parents[1], args.phase)


if __name__ == "__main__":
    sys.exit(main())
