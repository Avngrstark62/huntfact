from schemas import StartHuntRequest, StartHuntResponse
from logger import get_logger

logger = get_logger(__name__)


class HuntController:
    @staticmethod
    def start_hunt(request: StartHuntRequest) -> StartHuntResponse:
        logger.info(f"Starting hunt with video: {request.video_link}")
        
        try:
            result = StartHuntResponse(
                success=True,
                message="Hunt started successfully",
                result="this fact is true",
            )
            a=b
            logger.info("Hunt started successfully")
            return result
        except Exception as e:
            logger.error(f"Error starting hunt: {str(e)}", exc_info=True)
            raise
