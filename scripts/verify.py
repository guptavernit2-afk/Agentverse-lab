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
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        os.environ.pop(key, None)
    os.environ["AGENTVERSE_ENABLE_LIVE"] = "0"
    suites = [
        ("health", "scenario_schema"),
        ("kernel", "kernel_cli", "kernel_properties"),
        ("social", "observation"),
        ("policy",),
        ("store",),
        ("experiment",),
        ("dashboard_api",),
    ]
    pytest_args = ["--hypothesis-show-statistics"] if phase else []
    if phase < 7:
        pytest_args.extend(f"tests/test_{name}.py" for group in suites[:phase + 1] for name in group)
    python_test = [sys.executable, "-m"]
    if phase >= 7:
        python_test += ["coverage", "run", "--source=agentverse", "-m"]
    checks = [
        ("Backend import", [sys.executable, "-c", "import agentverse.api.main"], backend),
        ("Backend tests", [*python_test, "pytest", "-q", *pytest_args], backend),
        ("Frontend type check", [npm, "--offline", "run", "typecheck"], frontend),
        ("Frontend build", [npm, "--offline", "run", "build"], frontend),
    ]

    if phase >= 5:
        checks.append(("Paired offline demo", [sys.executable, str(root / "scripts/demo.py"),
                      "--mode", "rule_based", "--seed", "42", "--scenario", "food-scarcity"], root))
    if phase >= 6:
        os.environ["AGENTVERSE_VERIFICATION_PYTHON"] = sys.executable
        for label, target in (("Frontend lint", "lint"), ("Frontend unit tests", "test"),
                              ("Real backend browser workflow", "test:e2e")):
            checks.append((label, [npm, "--offline", "run", target], frontend))
    if phase >= 7:
        checks.append(("Critical module coverage", [sys.executable, str(root / "scripts/critical_coverage.py")], backend))
        checks.append(("Published experiment replay", [sys.executable, str(root / "scripts/check_export.py"),
                      str(root / "docs/verification/phase-7-pair.json")], root))
        checks.append(("Offline paired benchmark", [sys.executable, str(root / "scripts/benchmark.py")], root))
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
    parser.add_argument("--phase", type=int, choices=[0, 1, 2, 3, 4, 5, 6, 7], required=True)
    args = parser.parse_args()
    return verify(Path(__file__).resolve().parents[1], args.phase)


if __name__ == "__main__":
    sys.exit(main())
