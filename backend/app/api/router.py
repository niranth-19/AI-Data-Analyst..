from fastapi import APIRouter

from app.api.analyses import history_router, router as analyses_router
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(datasets_router)
api_router.include_router(analyses_router)
api_router.include_router(history_router)
api_router.include_router(reports_router)