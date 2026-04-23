from typing import List, Dict, Any
from logging_config import get_logger
from config import settings
from llm import llm
from chroma_client import chroma_client
from services.save_data_to_rag.save_data_to_rag import _get_embeddings

logger = get_logger("services.answer_questions.answer_questions")


async def answer_questions(job_id: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Answer questions using chunks retrieved from RAG.
    
    For each question/query in items, fetches top 3 chunks from RAG and sends
    to LLM for answering.
    
    Args:
        job_id: Job identifier to get the correct RAG collection
        items: List of item dictionaries with question and query
    
    Returns:
        List of items with answer field added
    """
    logger.info(f"Answering {len(items)} questions using RAG")
    
    collection_name = f"job_{job_id}"
    chroma = chroma_client.connect()
    
    try:
        collection = chroma.get_collection(name=collection_name)
    except Exception as e:
        logger.error(f"Failed to get collection {collection_name}: {str(e)}", exc_info=True)
        raise
    
    for item in items:
        question = item.get("question", "")
        query = item.get("query", "")
        
        try:
            logger.info(f"Answering question: {question}")
            
            query_embedding = _get_embeddings([query])[0]
            
            query_result = collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            
            chunks = []
            if query_result and query_result.get("documents"):
                chunks = query_result["documents"][0]
            
            logger.info(f"Retrieved {len(chunks)} chunks for query: {query}")
            
            chunks_text = "\n\n".join(chunks)
            
            prompt = f"""Based on the following chunks of information, answer the question:

QUESTION: {question}

CHUNKS:
{chunks_text}

Provide a clear and concise answer based only on the information provided in the chunks. If the chunks don't contain relevant information to answer the question, state that."""
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions based on provided context chunks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            result = await llm.call(
                model=settings.cheap_model,
                messages=messages,
            )
            
            answer = result

            logger.info(f"LLM response for question '{question}': {answer}")
            
            item["answer"] = answer
            
            logger.info(f"Answer generated for question: {question}")
        except Exception as e:
            logger.error(f"Error answering question '{question}': {e}", exc_info=True)
            item["answer"] = None
    
    logger.info(f"Completed answering {len(items)} questions")
    return items
