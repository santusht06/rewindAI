"""API v1 Router aggregation."""

from fastapi import APIRouter

from services.api.api.v1.admin import router as admin_router
from services.api.api.v1.assistant import router as assistant_router
from services.api.api.v1.companion import router as companion_router
from services.api.api.v1.questions import router as questions_router
from services.api.api.v1.sessions import router as sessions_router
from services.api.api.v1.titles import router as titles_router

api_v1_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_v1_router.include_router(titles_router)
api_v1_router.include_router(sessions_router)
api_v1_router.include_router(questions_router)
api_v1_router.include_router(companion_router)
api_v1_router.include_router(assistant_router)
api_v1_router.include_router(admin_router)

