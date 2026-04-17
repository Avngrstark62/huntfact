from typing import Dict, Any, List
from logging_config import get_logger
from config import settings
from chroma_client import chroma_client
from openai import OpenAI

logger = get_logger("services.save_data_to_rag.save_data_to_rag")


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


def _get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Get embeddings for texts using OpenAI embedding model.
    
    Args:
        texts: List of texts to embed
    
    Returns:
        List of embedding vectors
    """
    client = OpenAI(api_key=settings.openai_api_key)
    
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    
    embeddings = [item.embedding for item in response.data]
    logger.info(f"Generated embeddings for {len(embeddings)} texts")
    
    return embeddings


async def save_data_to_rag(job_id: str, pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Save fetched page data to ChromaDB with embeddings.
    
    Chunks page content, generates embeddings using OpenAI, and ingests into ChromaDB.
    
    Args:
        job_id: Job identifier for the collection
        pages_data: List of page data with url, title, and scraped_content
    
    Returns:
        Dictionary with rag_reference
    """
    logger.info(f"Starting save to RAG for job: {job_id}")
    logger.info(f"Processing {len(pages_data)} pages for RAG")
    
    chroma = chroma_client.connect()
    
    collection_name = f"job_{job_id}"
    try:
        collection = chroma.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        logger.error(f"Failed to create/get collection: {str(e)}", exc_info=True)
        raise
    
    documents = []
    ids = []
    metadatas = []
    chunk_count = 0
    
    for page_idx, page in enumerate(pages_data):
        url = page.get("url", "")
        title = page.get("title", "")
        content = page.get("scraped_content", "")
        
        if not content:
            logger.warning(f"Empty content for page: {url}")
            continue
        
        chunks = _chunk_text(content)
        logger.info(f"Split page {page_idx + 1} into {len(chunks)} chunks")
        
        for chunk_idx, chunk in enumerate(chunks):
            doc_id = f"{job_id}_{page_idx}_{chunk_idx}"
            documents.append(chunk)
            ids.append(doc_id)
            metadatas.append({
                "url": url,
                "title": title,
                "page_index": page_idx,
                "chunk_index": chunk_idx,
                "job_id": job_id
            })
            chunk_count += 1
    
    if not documents:
        logger.warning("No documents to ingest into ChromaDB")
        return {}
    
    logger.info(f"Generated {chunk_count} chunks, getting embeddings...")
    
    try:
        embeddings = _get_embeddings(documents)
    except Exception as e:
        logger.error(f"Failed to get embeddings: {str(e)}", exc_info=True)
        raise
    
    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully ingested {chunk_count} chunks into ChromaDB")
    except Exception as e:
        logger.error(f"Failed to ingest data into ChromaDB: {str(e)}", exc_info=True)
        raise
    
    logger.info(f"Data saved to ChromaDB for job: {job_id}")
    
    return {}

