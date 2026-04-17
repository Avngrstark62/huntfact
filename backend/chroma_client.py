import chromadb
from typing import Optional

from config import settings
from logging_config import get_logger

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
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                )
                self.is_healthy = True
                logger.info(f"Connected to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
            except Exception as e:
                self.is_healthy = False
                logger.error(f"Failed to connect to ChromaDB: {str(e)}", exc_info=True)
                raise ConnectionError(f"Failed to connect to ChromaDB: {str(e)}")
        
        return self.client
    
    def disconnect(self) -> None:
        """Close ChromaDB connection."""
        if self.client:
            self.client = None
            self.is_healthy = False
            logger.info("Disconnected from ChromaDB")


# ✅ singleton instance
chroma_client = ChromaDBClient()
