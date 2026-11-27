"""Measure complete persisted six-agent, eight-round pairs, excluding tool and GUI startup."""
from argparse import ArgumentParser
import json
from pathlib import Path
import platform
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

from agentverse.agents.policy import RulePolicy
from agentverse.experiments.scarcity import comparison, create_pair, execute, prepare
from agentverse.experiments.town import TownScenario
from agentverse.storage.store import Store


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, choices=range(3, 22), default=7)
    args = parser.parse_args()
    config = TownScenario.model_validate_json((Path(__file__).resolve().parents[1] / "scenarios/town-v1.json").read_bytes())
    seconds = []
    with TemporaryDirectory() as folder:
        for i in range(args.samples):
            db = Store(Path(folder) / f"{i}.sqlite")
            start = perf_counter()
            parent = prepare(db, "parent", config, 42)
            eid = create_pair(db, parent.run_id, parent.state.version)
            for label in "AB":
                execute(db, eid, label, RulePolicy())
            report = comparison(db, eid)
            elapsed = perf_counter() - start
            if report["completed_pairs"] != 1 or any(rows[-1]["scheduled_turns"] != 48 for rows in report["rounds"].values()):
                raise ValueError("incomplete benchmark sample")
            seconds.append(elapsed)
    measured = median(seconds)
    print(json.dumps({"platform": platform.platform(), "python": platform.python_version(), "seed": 42,
                      "samples_seconds": seconds, "median_seconds": measured, "target_seconds": 5}, indent=2))
    return int(measured >= 5)


if __name__ == "__main__":
    raise SystemExit(main())
