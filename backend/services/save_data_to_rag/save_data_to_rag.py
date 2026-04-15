from typing import Dict, Any
from logging_config import get_logger

logger = get_logger("services.save_data_to_rag.save_data_to_rag")


async def save_data_to_rag(gcs_reference: str, pages_data: list) -> Dict[str, Any]:
    """
    Save fetched page data to RAG (mocked).
    
    Takes GCS reference and pages data, and stores it in a mocked RAG system.
    Returns reference to stored RAG data.
    
    Args:
        gcs_reference: Reference to data in GCS
        pages_data: List of scraped page data
    
    Returns:
        Dictionary with RAG reference: {"rag_reference": "rag://ref-xyz"}
    """
    logger.info(f"Saving data to RAG from GCS reference: {gcs_reference}")
    logger.info(f"Processing {len(pages_data)} pages for RAG")
    
    rag_reference = f"rag://huntfact-data-{hash(gcs_reference) & 0x7fffffff}"
    
    logger.info(f"Data saved to RAG, reference: {rag_reference}")
    
    return {
        "rag_reference": rag_reference
    }
