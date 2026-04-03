from fastapi import APIRouter

from controllers.health import HealthController
from logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def get_health():
    """
    Health check endpoint.
    
    Returns the current server health status.
    """
    logger.debug("Health check requested")
    return HealthController.get_health()
