from typing import List, Dict, Any
from logging_config import get_logger
from config import settings
from llm import llm
from pydantic import BaseModel

logger = get_logger("services.extract_questions_queries.extract_questions_queries")


class QuestionQueryItem(BaseModel):
    question: str
    query: str


class ExtractedQuestionsResponse(BaseModel):
    items: List[QuestionQueryItem]


async def extract_questions_queries(utterances_english: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract factual claims and generate searchable questions/queries from conversation utterances.
    
    Analyzes utterances to identify claims that require verification via web search,
    excluding personal anecdotes, opinions, and unverifiable social media content.
    
    Args:
        utterances_english: List of translated utterance dictionaries
    
    Returns:
        List of question/query objects with structure:
        [
            {
                "question": "...",
                "query": "..."
            },
            ...
        ]
    """
    logger.info(f"Extracting questions and queries from {len(utterances_english)} utterances")
    
    if not utterances_english:
        logger.warning("No utterances to extract questions from")
        return []
    
    conversation_text = "\n".join([
        f"[{u['speaker']}]: {u['text']}" 
        for u in utterances_english
    ])
    
    prompt = f"""You are analyzing a conversation to identify factual claims that require web-based verification.

TASK:
Read the conversation and extract claims that should be fact-checked. For each claim:
1. Formulate it as a clear, standalone question
2. Convert that question to a concise web-searchable query

INCLUSION CRITERIA (Generate questions for):
- Specific factual claims about real events, statistics, policies, or documented facts
- Claims about public figures, organizations, institutions, or well-known entities
- Historical facts, scientific claims, or policy details that can be verified through web search
- Concrete data points like numbers, percentages, dates, or official information

EXCLUSION CRITERIA (Do NOT generate questions for):
- Personal anecdotes or private events mentioned in passing
- Personal opinions, beliefs, or subjective interpretations
- Local/personal controversies or social media drama that isn't publicly documented
- Information the speaker has direct personal knowledge of (unless it involves public figures/entities)
- Vague references to unnamed individuals' private lives or personal experiences
- Subjective assessments unless they're about measurable public impact
- Claims already explicitly stated as opinions, beliefs, or personal views

QUERY GENERATION PRINCIPLES:
- Keep queries concise (2-8 words typically)
- Use factual/objective phrasing suitable for web search engines
- Include key entities (people, organizations, concepts) that can be searched
- Avoid conversational language; use search-engine-friendly keywords
- Make queries specific enough to find relevant information, but broad enough to return results
- Remove unnecessary words while preserving meaning

CONVERSATION:
{conversation_text}

Generate questions and queries for ALL verifiable factual claims that can be web-searched.
Return a JSON structure with a list of items, where each item has a "question" and "query" field."""
    
    messages = [
        {
            "role": "system",
            "content": "You are an expert at identifying factual claims in conversations that require verification through web search. You understand the distinction between opinions, personal anecdotes, and verifiable facts."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    try:
        result = await llm.call_with_schema(
            model=settings.reasoning_model,
            messages=messages,
            schema_model=ExtractedQuestionsResponse,
        )
        
        items = [item.model_dump() for item in result.items]
        
        logger.info(f"Successfully extracted {len(items)} question/query items")
        
        return items
    except Exception as e:
        logger.error(f"Failed to extract questions and queries: {str(e)}", exc_info=True)
        raise

