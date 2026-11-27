"""Run the verification checks for an implemented project phase."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def verify_phase_zero(root: Path) -> int:
    backend = root / "backend"
    frontend = root / "frontend"
    npm_name = "npm.cmd" if os.name == "nt" else "npm"
    npm = shutil.which(npm_name) or npm_name
    checks = [
        ("Backend import", [sys.executable, "-c", "import agentverse.api.main"], backend),
        ("Backend tests", [sys.executable, "-m", "pytest", "-q"], backend),
        ("Frontend type check", [npm, "--offline", "run", "typecheck"], frontend),
        ("Frontend build", [npm, "--offline", "run", "build"], frontend),
    ]

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
    parser.add_argument("--phase", type=int, choices=[0], required=True)
    parser.parse_args()
    return verify_phase_zero(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    sys.exit(main())
