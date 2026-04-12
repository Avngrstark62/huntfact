from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field
from config import settings
from typing import Optional
from logging_config import get_logger
from agents.tools.web_search_tool import web_search_tool
from agents.tools.scrape_page_tool import scrape_page_tool

logger = get_logger("agents.claim_verifier")


class VerificationResult(BaseModel):
    claim: str = Field(..., description="The claim being verified")
    verdict: str = Field(
        ...,
        description="The verification verdict (VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, or FALSE)"
    )
    confidence: float = Field(
        ...,
        description="Confidence level from 0.0 to 1.0"
    )
    explanation: str = Field(
        ...,
        description="Detailed explanation of the verification result in a few sentences"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="URLs of sources used to verify the claim"
    )


_claim_verifier_agent: Optional[Agent] = None


def get_agent() -> Agent:
    global _claim_verifier_agent
    if _claim_verifier_agent is None:
        logger.info("Initializing ClaimVerifier Agent for the first time")
        _claim_verifier_agent = Agent(
            name="ClaimVerifier",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key
            ),
            tools=[web_search_tool, scrape_page_tool],
            output_schema=VerificationResult,
            description="You are an expert fact-checker specializing in verifying claims using web research.",
            instructions=[
                "You will receive a claim to verify (1-2 lines of text).",
                "Use the web_search tool to find relevant sources and information about the claim.",
                "Use guardrails to prevent excessive tool usage:",
                "  - Perform a maximum of 2-3 web searches to gather information.",
                "  - Only scrape pages that are directly relevant and promising (maximum 2-3 pages).",
                "  - Prioritize credible sources (news outlets, academic sources, government websites, etc.)",
                "  - Skip pages that are blocked, slow, or unlikely to contain relevant information.",
                "Evaluate the claim based on your research and assign a verdict:",
                "  - VERIFIED: The claim is supported by credible evidence.",
                "  - PARTIALLY_VERIFIED: The claim is partially true or contains nuance.",
                "  - UNVERIFIED: No evidence found to support or refute the claim.",
                "  - FALSE: The claim is contradicted by evidence.",
                "Provide a confidence score (0.0 to 1.0) based on the strength of evidence.",
                "Write an explanation in 2-4 sentences that clearly describes what you found and why you reached your verdict.",
                "Include URLs of sources you consulted in the 'sources' field.",
                "Be concise and efficient in your research to avoid unnecessary API calls."
            ],
        )
    return _claim_verifier_agent


async def verify_claim(claim: str) -> VerificationResult:
    """
    Verify a claim using web research tools with proper guardrails.
    
    Args:
        claim: The claim to verify (1-2 lines of text)
    
    Returns:
        VerificationResult with verdict, confidence, explanation, and sources
    """
    logger.info(f"Starting claim verification for: {claim}")
    
    # Retrieve the singleton instance
    agent = get_agent()
    
    formatted_input = f"""
    CLAIM TO VERIFY:
    ----------------
    {claim}
    ----------------
    
    Please verify this claim using your web search and research tools. Remember to use guardrails to avoid excessive tool usage.
    """
    
    try:
        logger.debug("Running claim verification agent")
        response = await agent.arun(formatted_input)
        
        if response and response.content:
            logger.info(f"Claim verification completed with verdict: {response.content.verdict}")
            return response.content
        else:
            logger.warning("Agent returned an empty response")
            return VerificationResult(
                claim=claim,
                verdict="UNVERIFIED",
                confidence=0.0,
                explanation="Unable to verify the claim due to agent error.",
                sources=[]
            )
            
    except Exception as e:
        logger.error(f"Error during claim verification: {str(e)}", exc_info=True)
        return VerificationResult(
            claim=claim,
            verdict="UNVERIFIED",
            confidence=0.0,
            explanation=f"An error occurred during verification: {str(e)}",
            sources=[]
        )
