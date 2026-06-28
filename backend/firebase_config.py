import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging
from logging_config import get_logger, log_event
from config import settings

logger = get_logger("firebase_config")

_initialized = False


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    
    Should be called once at application startup.
    """
    global _initialized
    
    if _initialized:
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="skipped",
            message="Firebase already initialized",
            component="firebase_config",
            provider="firebase",
            operation="initialize",
        )
        return
    
    try:
        service_account_path = settings.firebase.credentials_path
        
        if not os.path.exists(service_account_path):
            log_event(
                logger,
                level=logging.WARNING,
                event="provider.request.failed",
                status="failed",
                message="Firebase service account key not found",
                component="firebase_config",
                provider="firebase",
                operation="initialize",
                credentials_path=service_account_path,
            )
            return
        
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        
        _initialized = True
        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="Firebase Admin SDK initialized",
            component="firebase_config",
            provider="firebase",
            operation="initialize",
        )
        
    except Exception as e:
        log_event(
            logger,
            level=logging.ERROR,
            event="provider.request.failed",
            status="failed",
            message="Error initializing Firebase Admin SDK",
            component="firebase_config",
            provider="firebase",
            operation="initialize",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True,
        )
        _initialized = False
