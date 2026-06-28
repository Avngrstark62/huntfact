import chromadb
import logging
from typing import Optional

from config import settings
from logging_config import get_logger, log_event

logger = get_logger("chroma_client")


class ChromaDBClient:
    """ChromaDB client manager for vector storage."""
    
    def __init__(self):
        self.client: Optional[chromadb.HttpClient] = None
        self.is_healthy = False
    
    def connect(self) -> chromadb.HttpClient:
        """
        Get or create ChromaDB client instance.
        Initializes only once and reuses the connection.
        """
        if self.client is None:
            try:
                self.client = chromadb.HttpClient(
                    host=settings.chromadb.host,
                    port=settings.chromadb.port,
                )
                self.is_healthy = True
                log_event(
                    logger,
                    level=logging.INFO,
                    event="provider.request.succeeded",
                    status="succeeded",
                    message="Connected to ChromaDB",
                    component="chroma_client",
                    provider="chromadb",
                    operation="connect",
                    host=settings.chromadb.host,
                    port=settings.chromadb.port,
                )
            except Exception as e:
                self.is_healthy = False
                log_event(
                    logger,
                    level=logging.ERROR,
                    event="provider.request.failed",
                    status="failed",
                    message="Failed to connect to ChromaDB",
                    component="chroma_client",
                    provider="chromadb",
                    operation="connect",
                    host=settings.chromadb.host,
                    port=settings.chromadb.port,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True,
                )
                raise ConnectionError(f"Failed to connect to ChromaDB: {str(e)}")
        
        return self.client
    
    def disconnect(self) -> None:
        """Close ChromaDB connection."""
        if self.client:
            self.client = None
            self.is_healthy = False
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.succeeded",
                status="cancelled",
                message="Disconnected from ChromaDB",
                component="chroma_client",
                provider="chromadb",
                operation="disconnect",
            )


# ✅ singleton instance
chroma_client = ChromaDBClient()
