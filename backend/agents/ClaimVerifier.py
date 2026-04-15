from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from pydantic import BaseModel, Field
from config import settings
from typing import Optional
from logging_config import get_logger
from agents.tools.web_search_tool import web_search
from agents.tools.scrape_page_tool import scrape_page

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


_agent: Optional[Agent] = None


def _create_model():
    """Create model based on configured provider"""
    logger.info("Creating model instance")
    provider = settings.claim_extraction_model_provider.lower()
    model_name = settings.claim_extraction_model_name
    logger.info(f"Provider: {provider}, Model: {model_name}")
    
    if provider == "openai":
        logger.info("Creating OpenAIChat model")
        return OpenAIChat(
            id=model_name,
            api_key=settings.openai_api_key,
            temperature=0.1
        )
    elif provider == "google":
        logger.info("Creating Gemini model")
        return Gemini(
            id=model_name,
            api_key=settings.google_api_key,
            temperature=0.1
        )
    else:
        logger.error(f"Unsupported model provider: {provider}")
        raise ValueError(f"Unsupported model provider: {provider}")


def get_agent() -> Agent:
    global _agent
    logger.info("get_agent() called")
    if _agent is None:
        logger.info("Creating new ClaimVerifier Agent")
        
        logger.info("Creating model instance")
        model = _create_model()
        logger.info(f"Model created successfully: {type(model)}")
        
        logger.info("Creating Agent instance with tools")
        _agent = Agent(
            name="ClaimVerifier",
            model=model,
            tools=[web_search, scrape_page],
            output_schema=VerificationResult,
            description="You are an expert fact-checker specializing in verifying claims using web research.",
            tool_call_limit=10,
            instructions=[
    "You will receive a claim to verify (1-2 lines of text).",
    "",
    "ABSOLUTE RULE: You will follow exactly 2 phases and then STOP. No additional searches or scraping after Phase 2.",
    "",
    "FOLLOW THIS DECISION PROCESS:",
    "",
    "PHASE 1: INITIAL WEB SEARCH & SELECTIVE PAGE SCRAPING",
    "  1. Perform ONE initial web search with the claim or its key components.",
    "  2. Evaluate search results based on relevance, credibility, and alignment with the claim’s context.",
    "  3. Select 2-3 sources that are both credible and directly aligned with the subject, population, and context of the claim.",
    "  4. Scrape only the selected pages and extract information that directly relates to the claim.",
    "",
    "PHASE 2: REFINED FOLLOW-UP SEARCH (FINAL PHASE)",
    "  1. Identify gaps or uncertainties from Phase 1.",
    "  2. Perform ONE refined search targeting missing aspects of the claim.",
    "  3. Select and scrape at most 1-2 additional high-value sources.",
    "  4. After this phase, you MUST proceed to verification.",
    "",
    "EVIDENCE INTERPRETATION PRINCIPLES:",
    "  - Identify the scope and context implied by the claim before evaluating evidence.",
    "  - Evaluate evidence based on how well it aligns with the claim’s context, not just its topic.",
    "  - Treat evidence as strong only when it is directly applicable to the claim’s context.",
    "  - Treat loosely related or more general evidence as weak support rather than direct validation.",
    "  - Do not substitute convenient but mismatched evidence for directly relevant evidence.",
    "  - Distinguish between absence of evidence and contradiction:",
    "    * Absence of aligned evidence implies the claim is unverified.",
    "    * Evidence that is incompatible with the claim implies it is likely false.",
    "  - When evaluating quantitative or specific claims, ensure the scale and meaning are consistent with available evidence.",
    "VERDICT ASSIGNMENT:",
    "  You MUST assign one of the following based on the evidence:",
    "  - VERIFIED: Strong, direct, and consistent evidence supports the claim.",
    "  - PARTIALLY_VERIFIED: Some components are supported, while others are unsupported or inaccurate.",
    "  - UNVERIFIED: Evidence is insufficient, unclear, or not directly relevant to the claim.",
    "  - FALSE: Credible evidence directly contradicts the claim or makes it highly implausible.",
    "",
    "CONFIDENCE CALIBRATION:",
    "  - Confidence reflects the quality, consistency, and directness of evidence.",
    "  - High confidence requires multiple strong and relevant sources.",
    "  - Moderate confidence reflects partial alignment or some uncertainty.",
    "  - Low confidence reflects weak, indirect, or insufficient evidence.",
    "  - Do not reduce confidence solely due to missing evidence if strong contradictory evidence exists.",
    "",
    "FINAL OUTPUT REQUIREMENTS:",
    "  - Verdict: Choose one of the four categories.",
    "  - Confidence score (0.0 to 1.0): Reflect how strongly the evidence supports the verdict.",
    "  - Explanation (2-4 sentences): Summarize the relationship between the claim and the evidence.",
    "  - Sources: Include only the URLs of pages actually used.",
    "",
    "CRITICAL RULES:",
    "  - You WILL perform exactly 2 web searches maximum.",
    "  - You WILL NOT perform a third search.",
    "  - You MUST assign a verdict after Phase 2.",
    "  - You MUST rely on scraped content, not just snippets.",
    "  - Be selective in choosing sources and focus on relevance over quantity."
    ]
        )
        logger.info("Agent instance created successfully")
    else:
        logger.info("Returning existing agent instance")
    return _agent


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
    logger.debug("ClaimVerifier Agent initialized and ready")
    
    formatted_input = f"""
    CLAIM TO VERIFY:
    ----------------
    {claim}
    ----------------
    
    Please verify this claim using your web search and research tools. Remember to use guardrails to avoid excessive tool usage.
    """
    
    logger.debug(f"Formatted input: {formatted_input}")
    
    try:
        logger.debug("Running claim verification agent with tools: web_search, scrape_page")
        response = await agent.arun(formatted_input)
        logger.debug(f"Response received: {response}")
        
        # Log token usage metrics
        print(f"\n=== TOKEN USAGE ===")
        if hasattr(response, 'metrics') and response.metrics:
            print(f"Metrics: {response.metrics}")
        if hasattr(response, 'usage') and response.usage:
            print(f"Usage: {response.usage}")
        if hasattr(response, 'model_output'):
            print(f"Model output: {response.model_output}")
        # Print all attributes to find token info
        response_dict = vars(response) if hasattr(response, '__dict__') else {}
        print(f"All response attributes: {list(response_dict.keys())}")
        for key, value in response_dict.items():
            if 'token' in key.lower() or 'usage' in key.lower() or 'metric' in key.lower():
                print(f"  {key}: {value}")
        print(f"==================\n")
        
        if response and response.content:
            result = response.content
            logger.debug(f"Verdict: {result.verdict}")
            logger.info(f"Claim verification completed")
            logger.info(f"  Verdict: {result.verdict}")
            logger.info(f"  Confidence: {result.confidence}")
            logger.info(f"  Sources used: {len(result.sources)} - {result.sources}")
            return result
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
