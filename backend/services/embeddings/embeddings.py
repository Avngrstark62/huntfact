from typing import List

from openai import OpenAI

from config import settings
from logging_config import get_logger

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
    logger.info(f"Generated embeddings for {len(embeddings)} texts")

    return embeddings
