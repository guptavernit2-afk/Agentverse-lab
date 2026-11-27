import csv
from dataclasses import asdict
from io import StringIO

from agentverse.storage.store import Store, canonical
from .scarcity import comparison_in


def export_json(db: Store, eid: str) -> dict:
    with db.transaction() as sql:
        result = comparison_in(db, sql, eid)
        result["history"] = {label: [asdict(e) for e in db.load_in(sql, branch["run"]).events]
                             for label, branch in result["branches"].items()}
        return result


def export_csv(result: dict) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["experiment", "mode", "completed_pairs", "branch", "status", "round", "metric", "value"])
    for label, rows in result["rounds"].items():
        status = result["branches"][label]["status"]
        for row in rows:
            for name, value in row.items():
                if name != "round":
                    encoded = canonical(value) if isinstance(value, (dict, list)) else value
                    writer.writerow([result["manifest"]["experiment"], result["mode"], result["completed_pairs"],
                                     label, status, row["round"], name, encoded])
    return output.getvalue()
