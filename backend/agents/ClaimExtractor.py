from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field
from config import settings
from typing import List, Optional, Dict, Any
from logging_config import get_logger
import json

logger = get_logger("agents.claim_extractor")

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    severity: str = Field(..., description="Error severity: warning or critical")
    details: Dict[str, Any] = Field(default_factory=dict)

class DialogueSegment(BaseModel):
    speaker: str = Field(..., description="Speaker: creator, other, or unknown")
    text: str = Field(..., description="The text spoken")
    confidence: float = Field(..., description="Confidence score 0-1")

class Claim(BaseModel):
    claim: str = Field(..., description="The extracted claim")
    type: str = Field(..., description="Type: factual, opinion, or unclear")
    confidence: float = Field(..., description="Confidence score 0-1")
    source_span: str = Field(..., description="Exact supporting text from dialogue")

class ClaimExtractionResult(BaseModel):
    status: str = Field(..., description="Status: success, partial_success, or failure")
    errors: List[ErrorDetail] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    data: Dict[str, Any] = Field(default_factory=dict)

_agent: Optional[Agent] = None

def get_agent() -> Agent:
    global _agent
    if _agent is None:
        logger.info("Initializing Claim Extraction Agent")
        _agent = Agent(
            name="ClaimExtractorAgent",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key
            ),
            description="You are a precise information extraction system that performs translation, speaker identification, and claim extraction.",
            instructions=[
                "STEP 1 - TRANSLATION: Translate input text to English if not already English. Preserve meaning exactly, do not summarize.",
                "STEP 2 - SPEAKER IDENTIFICATION: Identify speakers (creator=person posting/narrating/reacting, other=quoted/referenced person, unknown=unclear). Structure into dialogue segments.",
                "STEP 3 - CLAIM EXTRACTION: Extract ONLY factual claims made by 'creator'. Claims must be objectively verifiable. Include exact source_span. Ignore opinions, emotions, rhetorical questions.",
                "Return ONLY valid JSON with this structure:",
                "{",
                '  "translated_text": "string",',
                '  "structured_dialogue": [{"speaker": "creator|other|unknown", "text": "string", "confidence": 0-1}],',
                '  "claims_by_creator": [{"claim": "string", "type": "factual|opinion|unclear", "confidence": 0-1, "source_span": "exact text"}]',
                "}"
            ],
        )
    return _agent

async def extract_claims(transcribed_text: str) -> ClaimExtractionResult:
    logger.info("Starting claim extraction")
    
    errors: List[ErrorDetail] = []
    status = "success"
    meta = {
        "input_language": "unknown",
        "confidence": 0.0,
        "notes": ""
    }
    data = {
        "translated_text": "",
        "structured_dialogue": [],
        "claims_by_creator": []
    }
    
    if not transcribed_text or not transcribed_text.strip():
        logger.error("Input text is empty or meaningless")
        errors.append(ErrorDetail(
            code="INVALID_INPUT",
            message="Input text is empty",
            severity="critical"
        ))
        return ClaimExtractionResult(
            status="failure",
            errors=errors,
            meta=meta,
            data=data
        )
    
    try:
        logger.info("Running claim extraction agent")
        agent = get_agent()
        response = await agent.arun(f"Process this text:\n{transcribed_text}")
        
        if not response or not response.content:
            logger.error("Agent returned empty response")
            errors.append(ErrorDetail(
                code="CLAIM_EXTRACTION_ERROR",
                message="Failed to extract claims",
                severity="critical"
            ))
            return ClaimExtractionResult(
                status="failure",
                errors=errors,
                meta=meta,
                data=data
            )
        
        try:
            response_text = response.content
            if isinstance(response_text, str):
                result_json = json.loads(response_text)
            else:
                result_json = response_text
            
            # Parse translated text
            if "translated_text" in result_json:
                data["translated_text"] = result_json["translated_text"]
            
            # Parse structured dialogue
            if "structured_dialogue" in result_json and isinstance(result_json["structured_dialogue"], list):
                for item in result_json["structured_dialogue"]:
                    segment = {
                        "speaker": item.get("speaker", "unknown"),
                        "text": item.get("text", ""),
                        "confidence": item.get("confidence", 0.5)
                    }
                    data["structured_dialogue"].append(segment)
            
            # Parse claims
            if "claims_by_creator" in result_json and isinstance(result_json["claims_by_creator"], list):
                for item in result_json["claims_by_creator"]:
                    claim = {
                        "claim": item.get("claim", ""),
                        "type": item.get("type", "unclear"),
                        "confidence": item.get("confidence", 0.5),
                        "source_span": item.get("source_span", "")
                    }
                    data["claims_by_creator"].append(claim)
            
            logger.info(f"Extracted {len(data['claims_by_creator'])} claims")
            meta["confidence"] = 0.8 if not errors else 0.6
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse response: {str(e)}")
            errors.append(ErrorDetail(
                code="CLAIM_EXTRACTION_ERROR",
                message="Failed to parse extraction results",
                severity="critical"
            ))
            status = "failure"
        
        logger.info(f"Claim extraction completed with status: {status}")
        return ClaimExtractionResult(
            status=status,
            errors=errors,
            meta=meta,
            data=data
        )
        
    except Exception as e:
        logger.error(f"Error during claim extraction: {str(e)}", exc_info=True)
        errors.append(ErrorDetail(
            code="CLAIM_EXTRACTION_ERROR",
            message=f"Unexpected error: {str(e)}",
            severity="critical"
        ))
        return ClaimExtractionResult(
            status="failure",
            errors=errors,
            meta=meta,
            data=data
        )
