from fastapi import HTTPException, status
from logger import get_logger

logger = get_logger(__name__)


class AppException(HTTPException):
    """Base application exception"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
    ):
        self.message = message
        self.error_code = error_code
        super().__init__(
            status_code=status_code,
            detail={
                "error": error_code,
                "message": message,
                "success": False,
            }
        )
        logger.error(f"{error_code}: {message}")


class ValidationException(AppException):
    """Validation error"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
        )


class ResourceNotFoundException(AppException):
    """Resource not found error"""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )
