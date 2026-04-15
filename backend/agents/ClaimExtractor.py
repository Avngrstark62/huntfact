from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from pydantic import BaseModel, Field
from config import settings
from typing import List, Optional
from logging_config import get_logger

logger = get_logger("agents.claim_extractor")

class Utterance(BaseModel):
    speaker: str
    text: str
    start: int
    end: int
    confidence: float

class ClaimExtractionResult(BaseModel):
    claims_list: List[str] = Field(description="A list of distinct claims extracted from all speakers' statements")
    opinions_list: List[str] = Field(description="A list of distinct opinions extracted from all speakers' statements")

_agent: Optional[Agent] = None

def _create_model():
    """Create model based on configured provider"""
    provider = settings.claim_extraction_model_provider.lower()
    model_name = settings.claim_extraction_model_name
    
    if provider == "openai":
        return OpenAIChat(
            id=model_name,
            api_key=settings.openai_api_key,
            temperature=0.1
        )
    elif provider == "google":
        return Gemini(
            id=model_name,
            api_key=settings.google_api_key,
            temperature=0.1
        )
    else:
        raise ValueError(f"Unsupported model provider: {provider}")

def get_agent() -> Agent:
    global _agent
    if _agent is None:
        logger.info(f"Initializing Claim Extraction Agent with {settings.claim_extraction_model_provider} provider")
        _agent = Agent(
            name="ClaimExtractorAgent",
            model=_create_model(),
            description="You are a claim extraction engine.",
            instructions=[
                "You are a claim extraction engine.",
                "",
                "Your task is to extract claims and opinions from the provided utterances.",
                "",
                "CORE PRINCIPLE:",
                "",
                "* Extract meaning, not surface text.",
                "* Operate on the intended idea being expressed, not on imperfect wording.",
                "",
                "INPUT NATURE:",
                "",
                "* The input may come from speech transcription and can contain minor errors, distortions, or unnatural phrasing.",
                "* Interpret statements in a way that best reflects their intended meaning when the surface form is clearly flawed.",
                "",
                "CLAIMS:",
                "",
                "* A claim is a factual assertion about the world that can be evaluated as true or false.",
                "* Represent each claim as a self-contained idea that stands independently.",
                "* Capture the full meaning required to understand the claim, but avoid including elements that do not change its factual content.",
                "* When multiple statements express the same underlying idea, unify them into a single claim.",
                "* Do not strengthen, weaken, or extend a claim beyond what is actually asserted.",
                "",
                "OPINIONS:",
                "",
                "* An opinion is a subjective judgment, evaluation, or normative stance.",
                "* Capture opinions as distinct ideas that reflect beliefs, preferences, or value judgments.",
                "* Ensure opinions remain separate from factual assertions even when they are closely related.",
                "",
                "MEANING RESOLUTION:",
                "",
                "* If a statement appears inconsistent, broken, or semantically invalid, resolve it using context when possible.",
                "* If a statement does not form a coherent idea even after interpretation, exclude it.",
                "* Prefer coherent meaning over literal but incorrect wording.",
                "",
                "SEPARATION:",
                "",
                "* Claims and opinions must be mutually exclusive.",
                "* Each extracted item should represent a single distinct idea.",
                "* Avoid overlap between items.",
                "",
                "MINIMALITY:",
                "",
                "* The output should be a minimal set of distinct ideas.",
                "* Do not include multiple items that express the same fact.",
                "* Do not fragment a single fact into multiple items.",
                "* Do not collapse multiple distinct facts into one, even if they support the same broader conclusion.",
                "",
                "SCOPE:",
                "",
                "* Extract claims and opinions from all speakers.",
                "* Do not filter based on speaker identity.",
                "",
                "OUTPUT:",
                "",
                "* Return only the final structured lists of claims and opinions.",
                "* Do not include explanations or intermediate reasoning."
            ],
            output_schema=ClaimExtractionResult,
        )
    return _agent

async def extract_claims(utterances: List[Utterance]) -> ClaimExtractionResult:
    logger.info("Starting claim extraction")
    
    if not utterances:
        logger.error("No utterances provided")
        return ClaimExtractionResult(
            claims_list=[],
            opinions_list=[]
        )
    
    agent = get_agent()
    response = await agent.arun(f"Extract claims and opinions from these utterances:\n\n{str([u.model_dump() for u in utterances])}")
    
    result = response.content
    logger.info(f"Successfully extracted {len(result.claims_list)} claims and {len(result.opinions_list)} opinions")
    return result
