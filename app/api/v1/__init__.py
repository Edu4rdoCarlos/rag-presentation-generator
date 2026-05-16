from fastapi import APIRouter

from app.api.v1.routes.feature import router as feature_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(feature_router)
