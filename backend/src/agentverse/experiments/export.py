import csv
import json
from dataclasses import asdict
from io import StringIO

from agentverse.storage.store import Store, canonical
from .scarcity import comparison_in


def export_json(db: Store, eid: str) -> dict:
    with db.transaction() as sql:
        result = comparison_in(db, sql, eid)
        result["history"] = {label: [asdict(e) for e in db.load_in(sql, branch["run"]).events]
                             for label, branch in result["branches"].items()}
        result["integrity"] = {}
        result["provider_attempts"] = {}
        for label, branch in result["branches"].items():
            run = branch["run"]
            head = sql.execute("SELECT head,head_hash,state_hash FROM runs WHERE id=?", (run,)).fetchone()
            result["integrity"][label] = {
                **dict(head), "run": run,
                "stream": [dict(r) for r in sql.execute(
                    "SELECT seq,schema,command,chain FROM events WHERE run=? ORDER BY seq", (run,))],
                "checkpoints": [dict(r) for r in sql.execute(
                    "SELECT seq,schema,digest FROM snapshots WHERE run=? ORDER BY seq", (run,))],
            }
            rows = sql.execute("SELECT before_version,actor,details FROM provider_attempts WHERE run=? ORDER BY ordinal",
                               (branch["run"],))
            result["provider_attempts"][label] = [{"before_version": row["before_version"], "actor": row["actor"],
                                                  **json.loads(row["details"])} for row in rows]
        return result


def export_csv(result: dict) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["experiment", "mode", "completed_pairs", "branch", "status", "round", "metric", "value"])
    def record(label, status, round_number, name, value):
        encoded = canonical(value) if isinstance(value, (dict, list)) else value
        writer.writerow([result["manifest"]["experiment"], result["mode"], result["completed_pairs"],
                         label, status, round_number, name, encoded])

    for label, rows in result["rounds"].items():
        branch = result["branches"][label]
        if not rows:
            record(label, branch["status"], "", "", None)
        for row in rows:
            for name, value in row.items():
                if name != "round":
                    record(label, branch["status"], row["round"], name, value)
        for name, value in branch["runtime"].items():
            record(label, branch["status"], "", f"runtime.{name}", value)
    for round_number, row in enumerate(result["deltas_by_round"], 1):
        for name, value in row.items():
            record("B-A", "complete", round_number, name, value)
    return output.getvalue()
