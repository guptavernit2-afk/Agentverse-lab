"""Offline developer fixture for exercising the simulation entry points."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from agentverse.domain.model import World
from agentverse.experiments.town import TownScenario
from agentverse.simulation.kernel import Kernel


def fixture_action(world: World, actor: str) -> dict:
    """A scripted smoke fixture for the six-agent baseline scenario."""
    if actor == "A1" and world.round == 1:
        return {"type": "CREATE_OFFER", "recipient_id": "A2", "quantity": 2,
                "price": 3, "expiry_round": min(2, len(world.scenario.harvest))}
    if actor == "A1" and world.round == 2:
        return {"type": "GIVE_FOOD", "recipient_id": "A2", "quantity": 1}
    if actor == "A1" and world.round == 3:
        return {"type": "CREATE_OFFER", "recipient_id": "A3", "quantity": 1,
                "price": 2, "expiry_round": min(5, len(world.scenario.harvest))}
    for offer in world.offers:
        if actor == offer.seller and world.round == 4 and offer.status == "open":
            return {"type": "REVOKE_OFFER", "offer_id": offer.id}
        if offer.buyer == actor and offer.status == "open":
            return {"type": "ACCEPT_OFFER", "offer_id": offer.id}
    if actor == "A2" and world.round in (3, 4):
        x, y = world.agent(actor).position
        return {"type": "MOVE", "x": x + 1, "y": y}
    profile = next(p for p in world.scenario.profiles if p.id == actor)
    return {"type": "WORK", "workplace": profile.workplace}


def social_action(world: World, actor: str) -> dict:
    if actor == "A1" and world.round == 1:
        return {"type": "CREATE_COMMITMENT", "beneficiary_id": "A2", "quantity": 2, "due_round": 3}
    if actor == "A2" and world.round == 1:
        return {"type": "SPEAK", "recipient_id": "board", "text": "I checked the harvest register.",
                "claim_ids": ["claim-harvest"], "evidence_ids": ["evidence-harvest"]}
    if actor == "A2" and world.round == 2:
        return {"type": "CREATE_COMMITMENT", "beneficiary_id": "A1", "quantity": 1, "due_round": 2}
    if actor == "A1" and world.round in (2, 3):
        for promise in world.social.commitments:
            if promise.promisor == actor and promise.outstanding:
                return {"type": "FULFILL_COMMITMENT", "commitment_id": promise.id, "quantity": 1}
    return {"type": "WAIT"}


def run(config: TownScenario, seed: int, fixture: str, run_id: str) -> dict:
    kernel = Kernel(config, seed, run_id=run_id)
    report = {"mode": "test_fixture", "view": "operator", "fixture": fixture, "seed": seed,
              "scenario_id": config.scenario_id, "initial_hash": kernel.state.digest(), "rounds": []}
    if fixture == "social":
        setup = [kernel.publish_harvest_claim(), kernel.issue_harvest_record(),
                 kernel.grant_evidence("evidence-harvest", grantee="A2")]
        report["setup_events"] = [asdict(event) for event in setup]
    while kernel.state.stage == "ready":
        events = [kernel.start_round()]
        order = kernel.state.order()
        while kernel.state.stage == "acting":
            turn = kernel.turn
            if fixture == "social":
                action = social_action(kernel.state, turn.actor)
            elif fixture == "economy":
                action = fixture_action(kernel.state, turn.actor)
            else:
                action = {"type": "WAIT"}
            events.append(kernel.submit(turn, action))
        events.append(kernel.settle_round())
        world = kernel.state
        report["rounds"].append({
            "round": world.round, "order": order, "events": [asdict(e) for e in events],
            "food": sum(a.food for a in world.agents), "agent_coins": sum(a.coins for a in world.agents),
            "treasury": world.treasury, "produced": world.produced, "consumed": world.consumed,
            "unmet": sum(a.unmet for a in world.agents), "hash": world.digest(),
        })
    if fixture == "social":
        report["commitments"] = [asdict(c) for c in kernel.state.social.commitments]
        report["trust"] = [asdict(edge) for edge in kernel.state.social.trust]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fixture", choices=["economy", "wait", "social"], default="economy")
    parser.add_argument("--run-id", default="cli")
    args = parser.parse_args()
    try:
        scenario = TownScenario.model_validate_json(args.scenario.read_bytes())
        report = run(scenario, args.seed, args.fixture, args.run_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
