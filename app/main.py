from fastapi import FastAPI

from app.api.v1 import api_v1_router
from app.core.config import settings

app = FastAPI(
    title="TestDoc Agent",
    description="Multi-agent system for automated test documentation generation.",
    version="0.1.0",
    debug=settings.app_debug,
)

app.include_router(api_v1_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
