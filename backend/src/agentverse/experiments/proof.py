"""Independently replay exported event streams, checkpoints and comparison values."""
import json

from agentverse.experiments.metrics import differences, trajectory
from agentverse.experiments.town import TownScenario
from agentverse.experiments.scarcity import BULLETIN, PROTOCOL
from agentverse.simulation.kernel import Kernel
from agentverse.storage.store import EVENT, SCHEMA, IntegrityError, canonical, chain_hash


def verify_export(data: dict) -> dict:
    manifest = data["manifest"]
    scenario = TownScenario.model_validate_json(json.dumps(manifest["scenario"]))
    if (manifest["protocol"] != PROTOCOL or manifest["policy"]["mode"] != data["mode"]
        or scenario.scenario_id != "food-scarcity" or scenario.harvest != (3,) * 8
        or manifest["planned_rounds"] != 8 or sum(p.food for p in scenario.profiles) != 18):
        raise IntegrityError("export protocol mismatch")
    if manifest["assignment"] != {"A": {"harvest_record_access": "private"}, "B": {"harvest_record_access": "public"}}:
        raise IntegrityError("export assignment mismatch")
    idx = manifest["checkpoint"]
    a, b = (data["history"][label] for label in "AB")
    if idx < 0 or a[:idx] != b[:idx] or len(b) <= idx:
        raise IntegrityError("export shared history mismatch")
    grant = b[idx]
    assigned = {"evidence_id": "evidence-harvest", "grantee": None}
    if (grant["kind"] != "EVIDENCE_GRANTED" or grant["grant"] != assigned
        or any(e["kind"] == "EVIDENCE_GRANTED" for e in a + b[idx + 1:])):
        raise IntegrityError("export treatment mismatch")
    heads = {}
    rounds = {}
    for label in "AB":
        proof = data["integrity"][label]
        run = manifest["children"][label]
        if proof["run"] != run or data["branches"][label]["run"] != run:
            raise IntegrityError("export run identity mismatch")
        kernel = Kernel(scenario, manifest["seed"], run_id=run)
        chain = kernel.state.digest()
        checkpoints = [{"seq": 0, "schema": SCHEMA, "digest": chain}]
        for event, saved in zip(data["history"][label], proof["stream"], strict=True):
            seq = kernel.state.version + 1
            raw = canonical(event)
            chain = chain_hash(chain, seq, saved["command"], raw)
            if saved["seq"] != seq or saved["schema"] != SCHEMA or saved["chain"] != chain:
                raise IntegrityError("export event chain mismatch")
            kernel.replay_event(EVENT.validate_json(raw, strict=True))
            if kernel.state.stage in {"ready", "finished"}:
                checkpoints.append({"seq": seq, "schema": SCHEMA, "digest": kernel.state.digest()})
        if (checkpoints != proof["checkpoints"] or kernel.state.version != proof["head"] or chain != proof["head_hash"]
            or kernel.state.digest() != proof["state_hash"] or kernel.world_at(manifest["checkpoint"]).digest() != manifest["prefix_hash"]):
            raise IntegrityError("export checkpoint or head mismatch")
        prefix = kernel.world_at(idx)
        if (prefix.round != 0 or prefix.stage != "ready" or prefix.social.grants
            or len(prefix.social.claims) != 1 or prefix.social.claims[0].text != BULLETIN
            or len(prefix.social.evidence) != 1):
            raise IntegrityError("export pre-intervention state mismatch")
        if data["branches"][label]["status"] == "complete" and kernel.state.stage != "finished":
            raise IntegrityError("export branch falsely marked complete")
        heads[label] = {"version": kernel.state.version, "state_hash": kernel.state.digest(), "checkpoints": len(checkpoints)}
        rounds[label] = trajectory(kernel)
        if rounds[label] != data["rounds"][label]:
            raise IntegrityError("export metric mismatch")
    complete = all(data["branches"][i]["status"] == "complete" and len(rounds[i]) == manifest["planned_rounds"] for i in "AB")
    deltas = [differences(a, b) for a, b in zip(rounds["A"], rounds["B"], strict=True)] if complete else []
    if data["completed_pairs"] != int(complete) or data["deltas_by_round"] != deltas or data["final_delta"] != (deltas[-1] if deltas else None):
        raise IntegrityError("export completion or delta mismatch")
    return {"experiment": manifest["experiment"], "mode": data["mode"], "prefix_hash": manifest["prefix_hash"], "branches": heads}
