from dataclasses import asdict
import asyncio
import json
import os
import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from agentverse.agents.gemini import GeminiPolicy, Limits
from agentverse.agents.policy import RulePolicy
from agentverse.experiments.export import export_csv, export_json
from agentverse.experiments.scarcity import comparison, create_pair, execute, get_pair, policy_settings, prepare
from agentverse.simulation.kernel import TurnConflict
from .control import command, status_in, tick

router = APIRouter()
ID_PATTERN = r"^[A-Za-z0-9_-]+$"
Id = Annotated[str, Path(min_length=1, max_length=100, pattern=ID_PATTERN)]
Key = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=ID_PATTERN)]
Version = Annotated[int, Field(ge=0, le=1000000)]


class Input(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class NewRun(Input):
    key: Key
    seed: Annotated[int, Field(ge=-2**31, lt=2**31)] = 42
    mode: Literal["rule_based"] = "rule_based"


class Control(Input):
    key: Key
    action: Literal["start", "pause", "step", "stop"]
    expected_version: Version
    expected_revision: Version
    delay: Annotated[float, Field(ge=0.1, le=10)] = 1


class Pair(Input):
    key: Key
    parent: Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=ID_PATTERN)]
    checkpoint: Version
    protocol: Literal["food-scarcity-v1"] = "food-scarcity-v1"
    mode: Literal["live_llm", "rule_based"] = "rule_based"
    approve_live: bool = False
    max_calls: Annotated[int, Field(gt=0, le=192)] | None = None
    max_tokens: Annotated[int, Field(gt=0, le=10000000)] | None = None


def live_model():
    model = os.getenv("AGENTVERSE_GEMINI_MODEL")
    if model and os.getenv("GEMINI_API_KEY") and os.getenv("AGENTVERSE_ENABLE_LIVE") == "1":
        return model
    return None


@router.get("/settings")
def settings():
    return {"live_model": live_model(), "provider": "gemini", "default_mode": "rule_based"}


@router.post("/runs", status_code=201)
def new_run(body: NewRun, request: Request):
    db = request.app.state.store
    name = "r-" + body.key
    try:
        prepare(db, name, request.app.state.town, body.seed)
    except sqlite3.IntegrityError:
        if db.load(name).state.seed != body.seed:
            raise TurnConflict("run key was reused") from None
    with db.transaction() as sql:
        return status_in(sql, name)


@router.get("/runs/{name}")
def metadata(name: Id, request: Request):
    with request.app.state.store.transaction() as sql:
        return status_in(sql, name)


async def advance(app, name, revision, delay):
    while True:
        await asyncio.sleep(delay)
        try:
            if not await asyncio.to_thread(tick, app.state.store, name, revision):
                break
        except (ValueError, sqlite3.DatabaseError):
            with app.state.store.transaction(write=True) as sql:
                sql.execute("UPDATE controls SET status='failed',revision=revision+1 "
                            "WHERE run=? AND revision=? AND status='running'", (name, revision))
            break


@router.post("/runs/{name}/control")
async def control(name: Id, body: Control, request: Request):
    app = request.app
    result = await asyncio.to_thread(command, app.state.store, name, body.model_dump())
    if body.action == "start":
        key = (name, result["revision"])
        if key not in app.state.tasks:
            task = asyncio.create_task(advance(app, *key, body.delay))
            app.state.tasks[key] = task
            task.add_done_callback(lambda _: app.state.tasks.pop(key, None))
    return result


def projection(k, seq=None):
    w = k.state if seq is None else k.world_at(seq)
    return {"view": "operator", "version": w.version, "state_hash": w.digest(),
            "world": json.loads(w.canonical()), "verified": True}


@router.get("/runs/{name}/world")
def world(name: Id, request: Request):
    return projection(request.app.state.store.load(name))


@router.get("/runs/{name}/agents/{actor}/view")
def agent_view(name: Id, actor: Id, request: Request, seq: Annotated[int | None, Query(ge=0)] = None):
    k = request.app.state.store.load(name)
    idx = k.state.version if seq is None else seq
    return {"view": "agent", "version": idx, "observation": k.observe(actor, version=idx).as_dict()}


@router.get("/runs/{name}/replay")
def replay(name: Id, request: Request, seq: Annotated[int, Query(ge=0)]):
    return projection(request.app.state.store.load(name), seq)


@router.get("/runs/{name}/snapshots")
def snapshots(name: Id, request: Request):
    return request.app.state.store.checkpoints(name)


@router.get("/runs/{name}/events")
def events(name: Id, request: Request, after: Annotated[int, Query(ge=0)] = 0,
           limit: Annotated[int, Query(ge=1, le=128)] = 64):
    k = request.app.state.store.load(name)
    if after > k.state.version:
        raise TurnConflict("cursor ahead of stream")
    page = k.events[after:after + limit]
    return {"events": [asdict(e) for e in page], "cursor": after + len(page), "head": k.state.version}


@router.websocket("/runs/{name}/stream")
async def stream(ws: WebSocket, name: Id, after: Annotated[int, Query(ge=0)] = 0):
    await ws.accept()
    db = ws.app.state.store
    cursor, revision = after, -1
    try:
        while True:
            with db.transaction() as sql:
                meta = status_in(sql, name)
            head = meta["version"]
            if cursor > head or head - cursor > 32:
                await ws.send_json({"type": "gap", "head": head, "after": cursor})
                await ws.close(code=1000)
                return
            if head != cursor or revision != meta["revision"]:
                await ws.send_json({"type": "update", "after": cursor, "head": head, "revision": meta["revision"]})
                cursor, revision = head, meta["revision"]
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=.25)
                if msg["type"] == "websocket.disconnect":
                    return
                await ws.close(code=1008)
                return
            except TimeoutError:
                pass
    except KeyError:
        await ws.close(code=1008)
    except WebSocketDisconnect:
        return


@router.post("/experiments", status_code=201)
def new_pair(body: Pair, request: Request):
    db = request.app.state.store
    policy = RulePolicy()
    if body.mode == "live_llm":
        model = live_model()
        if not model or not (body.approve_live and body.max_calls and body.max_tokens):
            raise HTTPException(422, "live model, explicit approval and limits required")
        policy = GeminiPolicy(model, os.getenv("GEMINI_API_KEY"), Limits(body.max_calls, body.max_tokens))
    eid = "e-" + body.key
    try:
        create_pair(db, body.parent, body.checkpoint, policy, experiment_id=eid)
    except sqlite3.IntegrityError:
        m = get_pair(db, eid)["manifest"]
        if (m["parent"], m["checkpoint"], m["policy"]) != (body.parent, body.checkpoint, policy_settings(policy)):
            raise TurnConflict("experiment key was reused") from None
    return get_pair(db, eid)


@router.get("/experiments/{eid}")
def experiment(eid: Id, request: Request):
    return get_pair(request.app.state.store, eid)


@router.post("/experiments/{eid}/branches/{label}/run")
def run_branch(eid: Id, label: Literal["A", "B"], request: Request):
    db = request.app.state.store
    manifest = get_pair(db, eid)["manifest"]
    saved = manifest["policy"]
    policy = RulePolicy()
    if saved["mode"] == "live_llm":
        if live_model() != saved["model"]:
            raise HTTPException(409, "approved live configuration unavailable")
        policy = GeminiPolicy(saved["model"], os.getenv("GEMINI_API_KEY"), Limits(**saved["limits"]))
    execute(db, eid, label, policy)
    return get_pair(db, eid)


@router.get("/experiments/{eid}/comparison")
def compare(eid: Id, request: Request):
    return comparison(request.app.state.store, eid)


@router.get("/experiments/{eid}/export")
def export(eid: Id, request: Request, format: Literal["json", "csv"] = "json"):
    data = export_json(request.app.state.store, eid)
    content = json.dumps(data, allow_nan=False) if format == "json" else export_csv(data)
    return Response(content, media_type="application/json" if format == "json" else "text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{eid}.{format}"'})
