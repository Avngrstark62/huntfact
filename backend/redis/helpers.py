import json
from typing import Any, Optional

from redis.client import redis_client
from logging_config import get_logger

logger = get_logger("redis")


def job_key(job_id: str) -> str:
    """Generate a Redis key for a job."""
    return f"job:{job_id}"


def set_job_data(
    job_id: str,
    data: Any,
    ttl: Optional[int] = None,
) -> None:
    """
    Store job data in Redis.
    
    Args:
        job_id: Unique job identifier
        data: Data to store (will be JSON serialized)
        ttl: Time to live in seconds (None = no expiration)
    """
    client = redis_client.connect()
    key = job_key(job_id)
    
    serialized_data = json.dumps(data)
    
    if ttl:
        client.setex(key, ttl, serialized_data)
        logger.debug(f"Stored job {job_id} with TTL {ttl}s")
    else:
        client.set(key, serialized_data)
        logger.debug(f"Stored job {job_id}")


def get_job_data(job_id: str) -> Optional[Any]:
    """
    Retrieve job data from Redis.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        The deserialized job data, or None if not found
    """
    client = redis_client.connect()
    key = job_key(job_id)
    
    data = client.get(key)
    if data is None:
        logger.debug(f"Job {job_id} not found in Redis")
        return None
    
    logger.debug(f"Retrieved job {job_id}")
    return json.loads(data)


def update_job_data(
    job_id: str,
    data: Any,
) -> None:
    """
    Update job data in Redis while preserving original TTL.
    
    Args:
        job_id: Unique job identifier
        data: Updated data to store (will be JSON serialized)
    """
    client = redis_client.connect()
    key = job_key(job_id)
    
    ttl = client.ttl(key)
    if ttl == -2:
        logger.warning(f"Job {job_id} not found in Redis during update")
        return
    
    serialized_data = json.dumps(data)
    
    if ttl == -1:
        client.set(key, serialized_data)
    else:
        client.setex(key, ttl, serialized_data)
    
    logger.debug(f"Updated job {job_id}")
    """
    Delete job data from Redis.
    
    Args:
        job_id: Unique job identifier
    """
    client = redis_client.connect()
    key = job_key(job_id)
    client.delete(key)
    logger.debug(f"Deleted job {job_id}")


def job_exists(job_id: str) -> bool:
    """
    Check if a job exists in Redis.
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        True if job exists, False otherwise
    """
    client = redis_client.connect()
    key = job_key(job_id)
    return client.exists(key) > 0


def get_job_ttl(job_id: str) -> Optional[int]:
    """
    Get remaining time to live for a job (in seconds).
    
    Args:
        job_id: Unique job identifier
    
    Returns:
        TTL in seconds, or None if key doesn't exist or has no expiration
    """
    client = redis_client.connect()
    key = job_key(job_id)
    ttl = client.ttl(key)
    
    if ttl == -2:  # Key doesn't exist
        return None
    if ttl == -1:  # Key exists but has no expiration
        return None
    
    return ttl
