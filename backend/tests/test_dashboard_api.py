import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from agentverse.api.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "lab.db"), base_url="http://127.0.0.1", client=("127.0.0.1", 51000)) as c:
        yield c


def new(c):
    response = c.post("/runs", json={"key": "test", "seed": 42})
    assert response.status_code == 201, response.text
    return response.json()


def control(c, meta, op, key, delay=.1):
    return c.post(f"/runs/{meta['id']}/control", json={"key": key, "action": op, "delay": delay,
                  "expected_revision": meta["revision"], "expected_version": meta["version"]})


def test_schema_and_local_boundary(client):
    c = client
    assert c.get("/openapi.json").json()["paths"]["/runs/{name}/agents/{actor}/view"]
    for payload in ({"key": "x", "actor": "A1"}, {"key": "bad/key"}, {"key": "x", "seed": "1"}):
        assert c.post("/runs", json=payload).status_code == 422
    assert c.post("/runs", content=b"x" * 17000).status_code == 413
    assert c.post("/runs", json={"key": "x"}, headers={"origin": "https://outside.example"}).status_code == 403
    assert c.get("/settings", headers={"host": "outside.example"}).status_code == 403
    assert c.get("/runs/missing").status_code == 404
    assert c.post("/runs/r-test/actions", json={"type": "GIVE_FOOD"}).status_code in (404, 405)
    assert c.post("/experiments", json={"key": "e", "parent": "r-test", "checkpoint": 2, "mode": "live_llm"}).status_code == 422


def test_control_retries_and_terminal_state(client):
    c = client
    meta = new(c)
    assert new(c) == meta
    assert c.post("/runs", json={"key": "test", "seed": 43}).status_code == 409
    one = control(c, meta, "step", "k").json()
    assert one["version"] == 10 and one["revision"] == 1
    assert control(c, meta, "step", "k").json() == one
    assert control(c, meta, "stop", "k").status_code == control(c, meta, "step", "j").status_code == 409
    running = control(c, one, "start", "start", delay=2).json()
    assert running["status"] == "running"
    paused = control(c, running, "pause", "pause").json()
    assert paused["status"] == "paused" and paused["version"] == one["version"]
    stopped = control(c, paused, "stop", "stop").json()
    assert stopped["status"] == "stopped" and control(c, stopped, "start", "again").status_code == 409


def test_stream_reconnect_and_gap(client):
    c = client
    meta = new(c)
    url = "ws://127.0.0.1/runs/r-test/stream"
    with c.websocket_connect(url + "?after=0") as ws:
        assert ws.receive_json() == {"type": "update", "after": 0, "head": 2, "revision": 0}
        meta = control(c, meta, "step", "step").json()
        assert ws.receive_json()["head"] == 10
    with c.websocket_connect(url + "?after=10") as ws:
        assert ws.receive_json()["after"] == 10
    for i in range(4):
        meta = control(c, meta, "step", str(i)).json()
    with c.websocket_connect(url + "?after=0") as ws:
        assert ws.receive_json() == {"type": "gap", "head": 42, "after": 0}
    page = c.get("/runs/r-test/events?after=5&limit=2").json()
    assert [e["sequence"] for e in page["events"]] == [6, 7] and page["cursor"] == 7
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect(url, headers={"origin": "https://outside.example"}):
            pass


def test_auto_run_and_pause(client):
    c = client
    meta = control(c, new(c), "start", "go").json()
    for _ in range(100):
        meta = c.get("/runs/r-test").json()
        if meta["status"] == "complete":
            break
        time.sleep(.03)
    assert meta["status"] == "complete" and meta["version"] == 66


def test_history_privacy_and_pair_api(client):
    c = client
    meta = new(c)
    body = {"key": "trial", "parent": meta["id"], "checkpoint": 2}
    pair = c.post("/experiments", json=body).json()
    assert c.post("/experiments", json=body).json() == pair
    eid = pair["manifest"]["experiment"]
    assert c.get(f"/experiments/{eid}/comparison").json()["final_delta"] is None
    for label in "AB":
        name = pair["branches"][label]["run"]
        view = c.get(f"/runs/{name}/agents/A1/view").json()
        assert view["view"] == "agent" and bool(view["observation"]["evidence"]) == (label == "B")
        assert c.get(f"/runs/{name}/agents/A1/view?seq=2").json()["observation"]["evidence"] == []
        assert c.get(f"/runs/{name}/replay?seq=2").json()["state_hash"] == pair["manifest"]["prefix_hash"]
        assert c.get(f"/runs/{name}/world").json()["view"] == "operator"
        assert control(c, c.get(f"/runs/{name}").json(), "step", "bad").status_code == 409
        assert c.post(f"/experiments/{eid}/branches/{label}/run").status_code == 200
    assert c.get(f"/experiments/{eid}/export?format=csv").text.startswith("experiment,mode")
    assert c.get(f"/experiments/{eid}/export").json()["completed_pairs"] == 1
