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

_translation_agent: Optional[Agent] = None
_speaker_agent: Optional[Agent] = None
_claim_agent: Optional[Agent] = None

def get_translation_agent() -> Agent:
    global _translation_agent
    if _translation_agent is None:
        logger.info("Initializing Translation Agent")
        _translation_agent = Agent(
            name="TranslationAgent",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key
            ),
            description="You are a precise translation expert.",
            instructions=[
                "Translate the input text to English if it's not already in English.",
                "Preserve the meaning exactly, do not summarize.",
                "If the text is already in English, return it unchanged.",
                "Return ONLY the translated text, nothing else.",
                "Respond in plain text format."
            ],
        )
    return _translation_agent

def get_speaker_agent() -> Agent:
    global _speaker_agent
    if _speaker_agent is None:
        logger.info("Initializing Speaker Identification Agent")
        _speaker_agent = Agent(
            name="SpeakerAgent",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key
            ),
            description="You are an expert at identifying speakers and structuring dialogue.",
            instructions=[
                "Analyze the text and identify speakers.",
                "'creator' = person posting/narrating/reacting",
                "'other' = any quoted, shown, or referenced person",
                "If unclear, mark as 'unknown'",
                "Split text into meaningful segments.",
                "Return ONLY valid JSON array with objects containing: speaker, text, confidence",
                "Example format: [{'speaker': 'creator', 'text': 'some text', 'confidence': 0.9}]"
            ],
        )
    return _speaker_agent

def get_claim_agent() -> Agent:
    global _claim_agent
    if _claim_agent is None:
        logger.info("Initializing Claim Extraction Agent")
        _claim_agent = Agent(
            name="ClaimAgent",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key
            ),
            description="You are an expert at extracting factual claims.",
            instructions=[
                "Extract ONLY claims made by 'creator'.",
                "A claim must be objectively verifiable (not pure opinion).",
                "Each claim must be independent (no duplicates, no merging unrelated ideas).",
                "Include exact supporting span for each claim.",
                "Ignore: opinions, emotional statements, rhetorical questions.",
                "Return ONLY valid JSON array with objects containing: claim, type, confidence, source_span",
                "Example format: [{'claim': 'text', 'type': 'factual', 'confidence': 0.9, 'source_span': 'exact text'}]"
            ],
        )
    return _claim_agent

async def extract_claims(transcribed_text: str) -> ClaimExtractionResult:
    logger.info("Starting three-step claim extraction process")
    
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
        # Step 1: Translation
        logger.info("Step 1: Translating text")
        translation_agent = get_translation_agent()
        translation_response = await translation_agent.arun(
            f"Translate to English if needed, otherwise return unchanged:\n{transcribed_text}"
        )
        
        if not translation_response or not translation_response.content:
            logger.error("Translation failed")
            errors.append(ErrorDetail(
                code="TRANSLATION_ERROR",
                message="Failed to translate text",
                severity="critical"
            ))
            status = "failure"
            return ClaimExtractionResult(
                status=status,
                errors=errors,
                meta=meta,
                data=data
            )
        
        translated_text = translation_response.content
        data["translated_text"] = translated_text
        logger.info("Translation completed")
        
        # Step 2: Speaker Identification
        logger.info("Step 2: Identifying speakers")
        speaker_agent = get_speaker_agent()
        speaker_response = await speaker_agent.arun(
            f"Identify speakers and structure dialogue:\n{translated_text}"
        )
        
        if speaker_response and speaker_response.content:
            try:
                dialogue_text = speaker_response.content
                if isinstance(dialogue_text, str):
                    dialogue_json = json.loads(dialogue_text)
                else:
                    dialogue_json = dialogue_text
                
                if isinstance(dialogue_json, list):
                    structured_dialogue = []
                    for item in dialogue_json:
                        segment = DialogueSegment(
                            speaker=item.get("speaker", "unknown"),
                            text=item.get("text", ""),
                            confidence=item.get("confidence", 0.5)
                        )
                        structured_dialogue.append(segment.model_dump())
                    data["structured_dialogue"] = structured_dialogue
                    logger.info(f"Identified {len(structured_dialogue)} dialogue segments")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse speaker dialogue: {str(e)}")
                errors.append(ErrorDetail(
                    code="SPEAKER_DETECTION_ERROR",
                    message="Failed to parse speaker identification",
                    severity="warning"
                ))
                status = "partial_success"
        else:
            logger.warning("Speaker identification returned empty response")
            errors.append(ErrorDetail(
                code="SPEAKER_DETECTION_ERROR",
                message="Speaker identification returned empty response",
                severity="warning"
            ))
            status = "partial_success"
        
        # Step 3: Claim Extraction
        logger.info("Step 3: Extracting claims from creator")
        claim_agent = get_claim_agent()
        
        dialogue_text_for_claims = translated_text
        if data["structured_dialogue"]:
            dialogue_text_for_claims = json.dumps(data["structured_dialogue"])
        
        claim_response = await claim_agent.arun(
            f"Extract factual claims made ONLY by 'creator':\n{dialogue_text_for_claims}"
        )
        
        if claim_response and claim_response.content:
            try:
                claims_text = claim_response.content
                if isinstance(claims_text, str):
                    claims_json = json.loads(claims_text)
                else:
                    claims_json = claims_text
                
                if isinstance(claims_json, list):
                    extracted_claims = []
                    for item in claims_json:
                        claim = Claim(
                            claim=item.get("claim", ""),
                            type=item.get("type", "unclear"),
                            confidence=item.get("confidence", 0.5),
                            source_span=item.get("source_span", "")
                        )
                        extracted_claims.append(claim.model_dump())
                    
                    data["claims_by_creator"] = extracted_claims
                    logger.info(f"Extracted {len(extracted_claims)} claims")
                    
                    if len(extracted_claims) == 0:
                        logger.info("No valid claims found")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse claims: {str(e)}")
                errors.append(ErrorDetail(
                    code="CLAIM_EXTRACTION_ERROR",
                    message="Failed to parse extracted claims",
                    severity="warning"
                ))
                if status == "success":
                    status = "partial_success"
        else:
            logger.info("No claims extracted (valid case)")
        
        # Check for low confidence
        overall_confidence = 0.8
        if errors:
            overall_confidence = 0.6
        
        meta["confidence"] = overall_confidence
        
        logger.info(f"Claim extraction completed with status: {status}")
        return ClaimExtractionResult(
            status=status,
            errors=errors,
            meta=meta,
            data=data
        )
        
    except Exception as e:
        logger.error(f"Error during claim extraction process: {str(e)}", exc_info=True)
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
