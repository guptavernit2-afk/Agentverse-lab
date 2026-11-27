import json
import os
from pathlib import Path
import subprocess
import sys

from agentverse.simulation.kernel import Kernel


def test_cli_is_deterministic_across_processes():
    scenario = Path(__file__).resolve().parents[2] / "scenarios" / "town-v1.json"
    traces = []
    for process_seed in ("17", "881"):
        result = subprocess.run(
            [sys.executable, "-m", "agentverse.cli", "--scenario", str(scenario),
             "--seed", "42", "--run-id", f"run-{process_seed}"],
            env={**os.environ, "PYTHONHASHSEED": process_seed}, capture_output=True, text=True, check=True,
        )
        traces.append(json.loads(result.stdout))
    a, b = traces
    assert a["mode"] == b["mode"] == "test_fixture"
    assert a["initial_hash"] == b["initial_hash"]
    assert len(a["rounds"]) == len(b["rounds"]) == 8
    for first, second in zip(a["rounds"], b["rounds"], strict=True):
        assert first == second, f"first divergent round: {first['round']}"
    assert len({r["hash"] for r in a["rounds"]} | {a["initial_hash"]}) == 9
    kinds = [e["kind"] for r in a["rounds"] for e in r["events"]]
    assert kinds.count("ACCEPT_OFFER") == 1 and kinds.count("GIVE_FOOD") == 1
    assert kinds.count("REVOKE_OFFER") == 1 and kinds.count("MOVE") == 2


def test_hash_detects_different_action_at_same_version(town):
    wait, work = (Kernel(town, 42, run_id=name) for name in ("left", "right"))
    for kernel in (wait, work):
        kernel.start_round()
    wait.submit(wait.turn, {"type": "WAIT"})
    work.submit(work.turn, {"type": "WORK", "workplace": "farm"})
    assert wait.state.version == work.state.version
    assert wait.state.digest() != work.state.digest()
