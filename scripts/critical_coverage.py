"""Fail the release if any critical module drops below 85% statement coverage."""
from io import StringIO
from pathlib import Path

from coverage import Coverage

BASE = Path("src/agentverse")
FILES = sorted(path for folder in ("domain", "simulation") for path in (BASE / folder).glob("*.py")
               if path.stem != "__init__") + [BASE / name for name in
               ("agents/observation.py", "experiments/town.py", "experiments/scenario_schema.py")]


def main():
    cov = Coverage()
    cov.load()
    files = [str(path) for path in FILES]
    cov.report(morfs=files, show_missing=True, precision=2)
    below = [path for path in files if cov.report(morfs=[path], file=StringIO()) < 85]
    if below:
        print("Below 85%:", ", ".join(below))
    return int(bool(below))


if __name__ == "__main__":
    raise SystemExit(main())
