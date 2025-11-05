"""
API v1 router configuration.
"""
from fastapi import APIRouter

from .auth import router as auth_router
# from .voice import router as voice_router  # Temporarily disabled
from .calendar import router as calendar_router
from .whatsapp import router as whatsapp_router
from .federated_learning import router as fedl_router
from .tasks import router as tasks_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
# api_router.include_router(voice_router, prefix="/voice", tags=["voice"])  # Temporarily disabled
api_router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
api_router.include_router(whatsapp_router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(fedl_router, tags=["federated-learning"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

# Placeholder for future routers
# api_router.include_router(agent_router, prefix="/agent", tags=["agent"])