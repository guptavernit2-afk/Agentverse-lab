import asyncio
from contextlib import asynccontextmanager
from importlib.metadata import version
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agentverse.experiments.scarcity import recover_branches
from agentverse.experiments.town import TownScenario
from agentverse.simulation.kernel import TurnConflict
from agentverse.storage.store import IntegrityError, Store
from .local import LocalBoundary
from .routes import router

ROOT = Path(__file__).resolve().parents[4]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


def create_app(database: Path | None = None):
    @asynccontextmanager
    async def lifespan(app):
        path = database or Path(os.getenv("AGENTVERSE_DB", str(ROOT / ".local/lab.sqlite")))
        path.parent.mkdir(parents=True, exist_ok=True)
        app.state.store = Store(path)
        app.state.town = TownScenario.model_validate_json((ROOT / "scenarios/town-v1.json").read_bytes())
        app.state.tasks = {}
        with app.state.store.transaction(write=True) as sql:
            sql.execute("UPDATE controls SET status='paused',revision=revision+1 WHERE status='running'")
            recover_branches(sql)
        try:
            yield
        finally:
            tasks = list(app.state.tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="AgentVerse Lab", version=version("agentverse-lab"), lifespan=lifespan, docs_url=None, redoc_url=None)
    app.add_middleware(LocalBoundary)
    app.include_router(router)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "record unavailable"}, 404)

    @app.exception_handler(TurnConflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, 409)

    @app.exception_handler(IntegrityError)
    async def corrupt(request, exc):
        return JSONResponse({"detail": "stored history failed integrity verification"}, 409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": "invalid operation or checkpoint"}, 422)

    @app.exception_handler(RequestValidationError)
    async def schema_error(request, exc):
        return JSONResponse({"detail": "invalid request fields"}, 422)

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(version=app.version)

    assets = ROOT / "frontend/dist"
    if assets.is_dir():
        app.mount("/", StaticFiles(directory=assets, html=True), name="dashboard")
    return app


app = create_app()
