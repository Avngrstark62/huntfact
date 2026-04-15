from typing import List, Dict, Any
from logging_config import get_logger

logger = get_logger("services.answer_questions.answer_questions")


async def answer_questions(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Answer questions using chunks from RAG (mocked).
    
    For each question/query in items, fetches chunks from RAG and sends
    to QA model to get answers.
    
    Args:
        items: List of item dictionaries with question and query
    
    Returns:
        List of items with answer field added
    """
    logger.info(f"Answering {len(items)} questions")
    
    for item in items:
        question = item.get("question", "")
        query = item.get("query", "")
        
        try:
            logger.info(f"Answering question: {question}")
            
            chunks = f"Mock chunks from RAG for query: {query}"
            
            answer = f"Mock answer to '{question}' based on retrieved chunks."
            
            item["answer"] = answer
            
            logger.info(f"Answer generated for question: {question}")
        except Exception as e:
            logger.error(f"Error answering question '{question}': {e}")
            item["answer"] = None
    
    logger.info(f"Completed answering {len(items)} questions")
    return items
