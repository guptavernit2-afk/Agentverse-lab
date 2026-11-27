"""Execute the registered pair locally and optionally export its complete artifacts."""
import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agentverse.agents.gemini import GeminiPolicy, Limits
from agentverse.agents.policy import RulePolicy
from agentverse.experiments.export import export_csv, export_json
from agentverse.experiments.scarcity import create_pair, execute, prepare
from agentverse.experiments.town import TownScenario
from agentverse.storage.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["rule_based", "live_llm"], default="rule_based")
    parser.add_argument("--scenario", choices=["food-scarcity"], default="food-scarcity")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--approve-live", action="store_true")
    args = parser.parse_args()
    policy = RulePolicy()
    if args.mode == "live_llm":
        key = os.environ.get("GEMINI_API_KEY")
        if not (args.approve_live and args.model and args.max_calls and args.max_tokens and key):
            parser.error("live mode requires explicit approval, a model, call and token limits, and a server key")
        policy = GeminiPolicy(args.model, key, Limits(args.max_calls, args.max_tokens))
    town = TownScenario.model_validate_json((Path(__file__).resolve().parents[1] / "scenarios/town-v1.json").read_bytes())
    with TemporaryDirectory() as tmp:
        directory = args.output or Path(tmp)
        directory.mkdir(parents=True, exist_ok=True)
        eid = uuid4().hex
        db = Store(directory / "lab.sqlite")
        parent = prepare(db, eid + "-parent", town, args.seed)
        create_pair(db, parent.run_id, parent.state.version, policy, experiment_id=eid)
        for label in ("A", "B"):
            execute(db, eid, label, policy)
        payload = export_json(db, eid)
        if args.output:
            (directory / f"{eid}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            (directory / f"{eid}.csv").write_text(export_csv(payload), encoding="utf-8")
        print(json.dumps({"experiment": eid, "mode": policy.mode, "completed_pairs": payload["completed_pairs"],
                          "outcomes": {label: {"status": branch["status"], "runtime": branch["runtime"],
                                               "unmet": rows[-1]["unmet_units"] if rows else None}
                                       for label, branch in payload["branches"].items() for rows in [payload["rounds"][label]]},
                          "delta_unmet": (payload["final_delta"] or {}).get("unmet_units")}, indent=2))
        return 0 if payload["completed_pairs"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
