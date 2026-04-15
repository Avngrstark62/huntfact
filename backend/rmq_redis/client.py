import redis as redis_lib
from typing import Optional

from config import settings
from logging_config import get_logger

logger = get_logger("redis")


class RedisClient:
    """Redis client manager for job data storage."""
    
    def __init__(self):
        self.client: Optional[redis_lib.Redis] = None
        self.is_healthy = False
    
    def connect(self) -> redis_lib.Redis:
        """
        Get or create Redis client instance.
        Initializes only once and reuses the connection.
        """
        if self.client is None:
            try:
                self.client = redis_lib.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password if settings.redis_password else None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )
                self.client.ping()
                self.is_healthy = True
                logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
            except Exception as e:
                self.is_healthy = False
                logger.error(f"Failed to connect to Redis: {str(e)}", exc_info=True)
                raise ConnectionError(f"Failed to connect to Redis: {str(e)}")
        
        return self.client
    
    def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.is_healthy = False
            logger.info("Disconnected from Redis")


# ✅ singleton instance
redis_client = RedisClient()
