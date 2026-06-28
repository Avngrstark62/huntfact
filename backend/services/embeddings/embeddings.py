from typing import List
import logging

from openai import OpenAI

from config import settings
from logging_config import get_logger, log_event

logger = get_logger("services.embeddings.embeddings")


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Get embeddings for texts using OpenAI embedding model.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    client = OpenAI(api_key=settings.openai.api_key)

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )

    embeddings = [item.embedding for item in response.data]
    log_event(
        logger,
        level=logging.INFO,
        event="provider.request.succeeded",
        status="succeeded",
        message="Generated embeddings",
        component="services.embeddings",
        provider="openai",
        operation="embeddings.create",
        result_summary={"embedding_count": len(embeddings)},
    )

    return embeddings
