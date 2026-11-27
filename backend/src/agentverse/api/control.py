"""Durable operator controls. Each tick commits one settled offline round."""
import json
from uuid import uuid4

from agentverse.agents.policy import RulePolicy
from agentverse.simulation.kernel import TurnConflict
from agentverse.simulation.runner import step
from agentverse.storage.store import Store, canonical


def status_in(sql, name: str) -> dict:
    row = sql.execute("SELECT head,seed FROM runs WHERE id=?", (name,)).fetchone()
    if row is None:
        raise KeyError(name)
    ctrl = sql.execute("SELECT status,revision,delay FROM controls WHERE run=?", (name,)).fetchone()
    b = sql.execute("SELECT b.status,e.manifest FROM branches b JOIN experiments e ON b.experiment=e.id WHERE b.run=?",
                    (name,)).fetchone()
    return {"id": name, "version": row["head"], "seed": row["seed"], "revision": ctrl["revision"] if ctrl else 0,
            "status": b["status"] if b else ctrl["status"] if ctrl else "paused",
            "mode": json.loads(b["manifest"])["policy"]["mode"] if b else "rule_based",
            "read_only": b is not None, "delay": ctrl["delay"] if ctrl else 1.0}


def settle_next(kernel):
    if kernel.state.stage == "finished":
        raise TurnConflict("run completed")
    policy = RulePolicy()
    while step(kernel, policy).kind != "ROUND_SETTLED":
        pass


def command(db: Store, name: str, body: dict):
    request = canonical(body)
    key = body["key"]
    with db.transaction(write=True) as sql:
        prior = sql.execute("SELECT * FROM control_results WHERE run=? AND key=?", (name, key)).fetchone()
        if prior:
            if prior["request"] != request:
                raise TurnConflict("command key was reused")
            return json.loads(prior["response"])
        old = status_in(sql, name)
        if old["read_only"]:
            raise TurnConflict("experiment branches are controlled by the protocol")
        if (old["version"], old["revision"]) != (body["expected_version"], body["expected_revision"]):
            raise TurnConflict("stale control request")
        if old["status"] in {"stopped", "complete", "failed"}:
            raise TurnConflict("run is terminal")
        action = body["action"]
        if action == "step":
            if old["status"] == "running":
                raise TurnConflict("pause before stepping")
            kernel = db.load_in(sql, name)
            settle_next(kernel)
            db.save_in(sql, kernel, old["version"], "operator-" + key, request)
            status = "complete" if kernel.state.stage == "finished" else "paused"
        else:
            status = {"start": "running", "pause": "paused", "stop": "stopped"}[action]
        sql.execute("INSERT OR REPLACE INTO controls VALUES (?,?,?,?)",
                    (name, status, old["revision"] + 1, body["delay"]))
        result = status_in(sql, name)
        sql.execute("INSERT INTO control_results VALUES (?,?,?,?)", (name, key, request, canonical(result)))
        return result


def tick(db: Store, name: str, revision: int) -> bool:
    with db.transaction(write=True) as sql:
        current = status_in(sql, name)
        if current["revision"] != revision or current["status"] != "running":
            return False
        kernel = db.load_in(sql, name)
        settle_next(kernel)
        db.save_in(sql, kernel, current["version"], "tick-" + uuid4().hex, "scheduled round")
        if kernel.state.stage == "finished":
            sql.execute("UPDATE controls SET status='complete', revision=revision+1 WHERE run=?", (name,))
            return False
        return True
