from fastapi import APIRouter

from app.api.routes.feature import router as feature_router

api_router = APIRouter(prefix="/api")
api_router.include_router(feature_router)
