from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field
from config import settings
from typing import List, Optional
from logging_config import get_logger

logger = get_logger("agents.claim_extractor")

class ClaimList(BaseModel):
    claims: List[str] = Field(..., description="List of extracted claims")

# 1. Change the global variable to a private placeholder
_claim_agent: Optional[Agent] = None

# 2. Add a getter function to handle the Singleton logic
def get_agent() -> Agent:
    global _claim_agent
    if _claim_agent is None:
        logger.info("Initializing ClaimExtractor Agent for the first time")
        _claim_agent = Agent(
            name="ClaimExtractor",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key
            ),
            output_schema=ClaimList,
            description="You are an expert at extracting claims from video transcripts.",
            instructions=[
                "Analyze the text provided in the 'Transcribed Text' section below.",
                "Extract ONLY claims made by the creator.",
                "Ignore all other speakers."
            ],
        )
    return _claim_agent

async def extract_claims(transcribed_text: str) -> List[str]:
    logger.info("Starting claim extraction from transcribed text")
    
    # 3. Retrieve the singleton instance
    agent = get_agent()
    
    formatted_input = f"""
    TRANSCRIPTION DATA START
    ------------------------
    {transcribed_text}
    ------------------------
    TRANSCRIPTION DATA END
    """
    
    try:
        logger.debug("Running claim extraction agent")
        # Ensure you use .arun() for async!
        response = await agent.arun(formatted_input)
        
        if response and response.content:
            claims_found = response.content.claims
            logger.info(f"Successfully extracted {len(claims_found)} claims")
            return claims_found
        else:
            logger.warning("Agent returned an empty response")
            return []
            
    except Exception as e:
        logger.error(f"Error during claim extraction: {str(e)}", exc_info=True)
        return []
