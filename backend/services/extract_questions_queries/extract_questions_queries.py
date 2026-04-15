from typing import List, Dict, Any
from logging_config import get_logger

logger = get_logger("services.extract_questions_queries.extract_questions_queries")


async def extract_questions_queries(utterances_english: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract questions and queries from English utterances.
    
    Currently returns hardcoded example items.
    Will be implemented with actual extraction logic later.
    
    Args:
        utterances_english: List of translated utterance dictionaries
    
    Returns:
        List of question/query objects with structure:
        [
            {
                "id": "q1",
                "question": "...",
                "query": "..."
            },
            ...
        ]
    """
    logger.info(f"Extracting questions and queries from {len(utterances_english)} utterances")
    
    # Template: Return hardcoded items for now
    # TODO: Implement actual extraction logic
    items = [
        {
            "id": "q1",
            "question": "What is the capital of France?",
            "query": "capital of France"
        },
        {
            "id": "q2",
            "question": "How does photosynthesis work?",
            "query": "photosynthesis process"
        },
        {
            "id": "q3",
            "question": "What are the benefits of exercise?",
            "query": "benefits of exercise"
        }
    ]
    
    return items
