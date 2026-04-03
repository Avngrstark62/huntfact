from fastapi import APIRouter, status

from controllers.hunt import HuntController
from schemas import StartHuntRequest, StartHuntResponse
from logger import get_logger
from exceptions import ValidationException

logger = get_logger(__name__)
router = APIRouter(prefix="/hunts", tags=["hunts"])


@router.post("/start-hunt", response_model=StartHuntResponse, status_code=status.HTTP_200_OK)
def start_hunt(request: StartHuntRequest) -> StartHuntResponse:
    """
    Start a new hunt with a video link.
    
    - **video_link**: URL of the video to analyze
    
    Returns the hunt result and status.
    """
    try:
        return HuntController.start_hunt(request)
    except ValueError as e:
        logger.warning(f"Validation error in start_hunt: {str(e)}")
        raise ValidationException(str(e))
    except Exception as e:
        logger.error(f"Unexpected error in start_hunt: {str(e)}", exc_info=True)
        raise
