# Redis Module

This module provides a simple interface for storing and retrieving job data in Redis.

## Quick Usage

### Basic Setup

```python
from redis import set_job_data, get_job_data, delete_job_data
```

### Store Job Data

```python
job_id = "my-job-123"
job_data = {
    "items": [
        {
            "id": "q1",
            "question": "...",
            "query": "...",
            "urls": [],
            "chunks": [],
            "answer": None
        }
    ]
}

# Store with no expiration
set_job_data(job_id, job_data)

# Or store with 24-hour expiration (86400 seconds)
set_job_data(job_id, job_data, ttl=86400)
```

### Retrieve Job Data

```python
data = get_job_data("my-job-123")
if data:
    print(data["items"])
```

### Update Job Data

```python
data = get_job_data("my-job-123")
data["items"][0]["urls"].append("https://example.com")
set_job_data("my-job-123", data)  # Save updated data
```

### Delete Job Data

```python
delete_job_data("my-job-123")
```

## Configuration

By default, the client connects to `localhost:6379`. To use a different Redis server:

```python
from redis import get_redis_client

client = get_redis_client(host="your-redis-host", port=6379)
```

Set these via environment variables in your app config if using a remote server.
