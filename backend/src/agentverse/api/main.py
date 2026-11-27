from importlib.metadata import version
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


app = FastAPI(title="AgentVerse Lab", version=version("agentverse-lab"))


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(version=app.version)
