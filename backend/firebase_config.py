import firebase_admin
from firebase_admin import credentials, messaging
import os
from logging_config import get_logger
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
        logger.info("Firebase already initialized")
        return
    
    try:
        service_account_path = settings.firebase_credentials_path
        
        if not os.path.exists(service_account_path):
            logger.warning(f"Firebase service account key not found at {service_account_path}")
            return
        
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        
        _initialized = True
        logger.info("Firebase Admin SDK initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {e}", exc_info=True)
        _initialized = False
