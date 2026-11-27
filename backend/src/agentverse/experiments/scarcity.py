"""Pre-registered eight-round evidence-access experiment and independent branch execution."""
from dataclasses import asdict
from importlib.metadata import version
import json
from time import perf_counter
from uuid import uuid4

from agentverse.agents.gemini import GeminiPolicy
from agentverse.agents.policy import RulePolicy
from agentverse.experiments.town import TownScenario
from agentverse.simulation.runner import run
from agentverse.storage.store import Store, canonical
from .metrics import differences, trajectory

BULLETIN = "The next eight rounds may have reduced harvests."
PROTOCOL = "food-scarcity-v1"


def scarcity(town: TownScenario) -> TownScenario:
    config = town.model_dump()
    config.update(scenario_id="food-scarcity", harvest=(3,) * 8)
    special = TownScenario.model_validate(config)
    if sum(a.food for a in special.profiles) != 18:
        raise ValueError("protocol requires 18 initial food")
    return special


def prepare(db: Store, name: str, town: TownScenario, seed: int):
    with db.transaction(write=True) as sql:
        k = db.create_in(sql, name, scarcity(town), seed)
        k.publish_harvest_claim(BULLETIN)
        k.issue_harvest_record()
        db.save_in(sql, k, 0, "setup", PROTOCOL)
        return k


def policy_settings(policy):
    config = {"mode": policy.mode, "policy_version": policy.version, "model": None, "prompt_version": None}
    if isinstance(policy, GeminiPolicy):
        config.update(model=policy.model, provider="gemini", prompt_version=policy.prompt_version,
                      temperature=0, model_seed=None, limits=asdict(policy.limits))
    elif type(policy) is not RulePolicy:
        raise ValueError("unsupported experimental policy")
    return config


def create_pair(db: Store, parent: str, seq: int, policy=None, *, experiment_id: str | None = None) -> str:
    eid = experiment_id or uuid4().hex
    settings = policy_settings(policy if policy is not None else RulePolicy())
    children = {label: f"{eid}-{label}" for label in ("A", "B")}
    with db.transaction(write=True) as sql:
        k = db.load_in(sql, parent)
        w = k.world_at(seq)
        if (w.round != 0 or w.stage != "ready" or w.scenario.scenario_id != "food-scarcity"
            or w.scenario.harvest != (3,) * 8 or sum(a.food for a in w.agents) != 18
            or len(w.social.claims) != 1 or w.social.claims[0].text != BULLETIN
            or len(w.social.evidence) != 1 or w.social.grants):
            raise ValueError("protocol requires the pre-intervention scarcity checkpoint")
        db.fork_in(sql, parent, seq, tuple(children.values()))
        manifest = {"experiment": eid, "protocol": PROTOCOL, "engine": version("agentverse-lab"),
                    "scenario": w.scenario.model_dump(mode="json"), "parent": parent, "checkpoint": seq,
                    "prefix_hash": w.digest(), "seed": w.seed, "policy": settings, "children": children,
                    "assignment": {"A": {"harvest_record_access": "private"},
                                   "B": {"harvest_record_access": "public"}},
                    "primary_metric": "unmet_units", "planned_rounds": 8, "planned_pairs": 1}
        sql.execute("INSERT INTO experiments VALUES (?,?)", (eid, canonical(manifest)))
        for label, child in children.items():
            sql.execute("INSERT INTO branches VALUES (?,?,?,?,?)", (eid, label, child, "ready", "{}"))
        b = db.load_in(sql, children["B"])
        b.grant_evidence("evidence-harvest", grantee=None)
        db.save_in(sql, b, seq, "treatment", "public harvest record")
    return eid


def get_pair(db: Store, eid: str) -> dict:
    with db.transaction() as sql:
        return pair_in(sql, eid)


def pair_in(sql, eid: str) -> dict:
    row = sql.execute("SELECT manifest FROM experiments WHERE id=?", (eid,)).fetchone()
    if row is None:
        raise KeyError(eid)
    branches = {r["label"]: {"status": r["status"], "run": r["run"], "runtime": json.loads(r["telemetry"])}
                for r in sql.execute("SELECT * FROM branches WHERE experiment=? ORDER BY label", (eid,))}
    return {"manifest": json.loads(row[0]), "branches": branches}


def execute(db: Store, eid: str, label: str, policy):
    pair = get_pair(db, eid)
    if policy_settings(policy) != pair["manifest"]["policy"]:
        raise ValueError("policy configuration mismatch")
    branch = pair["branches"][label]
    if branch["status"] != "ready":
        return branch["status"]
    # Claim execution before any external request. A crash leaves a visible interrupted run.
    with db.transaction(write=True) as sql:
        if isinstance(policy, GeminiPolicy):
            previous = sql.execute("SELECT status,telemetry FROM branches WHERE experiment=? AND label<>?", (eid, label)).fetchone()
            if previous["status"] in {"running", "interrupted"}:
                raise ValueError("previous live allowance unresolved")
            spent = json.loads(previous["telemetry"])
            policy.attempts = max(policy.attempts, spent.get("calls", 0))
            policy.reserved_tokens = max(policy.reserved_tokens, spent.get("reserved_tokens", 0))
        claimed = sql.execute("UPDATE branches SET status='running' WHERE run=? AND status='ready'", (branch["run"],))
        if not claimed.rowcount:
            raise ValueError("branch execution already claimed")
    k = db.load(branch["run"])
    initial = k.state.version
    live = isinstance(policy, GeminiPolicy)
    before = (policy.attempts, policy.reported_tokens, policy.reserved_tokens) if live else (0, 0, 0)
    counters = ("retries", "input_tokens", "output_tokens", "usage_responses")
    initial_counts = {key: getattr(policy, key, 0) for key in counters}
    started = perf_counter()
    try:
        status = run(k, policy)
    except BaseException:
        with db.transaction(write=True) as sql:
            db.save_in(sql, k, initial, "execute", "experiment")
            sql.execute("UPDATE branches SET status='interrupted' WHERE run=?", (branch["run"],))
        raise
    calls = policy.attempts - before[0] if live else 0
    telemetry = {"seconds": perf_counter() - started, "calls": calls,
                 "reported_tokens": policy.reported_tokens - before[1] if live else 0,
                 "reserved_tokens": policy.reserved_tokens - before[2] if live else 0,
                 "estimated_cost": None if live else 0}
    for key in counters:
        telemetry[key] = getattr(policy, key, 0) - initial_counts[key]
    telemetry["usage_complete"] = telemetry["usage_responses"] == calls
    if live and calls and not telemetry["usage_responses"]:
        for key in ("reported_tokens", "input_tokens", "output_tokens"):
            telemetry[key] = None
    if live and policy.limits.price_per_million is not None:
        telemetry["estimated_cost"] = telemetry["reserved_tokens"] * policy.limits.price_per_million / 1_000_000
    with db.transaction(write=True) as sql:
        db.save_in(sql, k, initial, "execute", "experiment")
        sql.execute("UPDATE branches SET status=?,telemetry=? WHERE run=?",
                    (status, canonical(telemetry), branch["run"]))
    return status


def comparison(db: Store, eid: str) -> dict:
    with db.transaction() as sql:
        return comparison_in(db, sql, eid)


def comparison_in(db, sql, eid):
    pair = pair_in(sql, eid)
    rows = {label: trajectory(db.load_in(sql, branch["run"])) for label, branch in pair["branches"].items()}
    complete = all(b["status"] == "complete" and len(rows[label]) == 8 for label, b in pair["branches"].items())
    deltas = [differences(a, b) for a, b in zip(rows["A"], rows["B"], strict=True)] if complete else []
    return {**pair, "rounds": rows, "completed_pairs": int(complete), "mode": pair["manifest"]["policy"]["mode"],
            "deltas_by_round": deltas, "final_delta": deltas[-1] if deltas else None}
