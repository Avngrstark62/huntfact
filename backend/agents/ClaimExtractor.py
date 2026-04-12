from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field, ValidationError
from config import settings
from typing import List, Optional, Dict, Any
from logging_config import get_logger
import json

logger = get_logger("agents.claim_extractor")

class ErrorDetail(BaseModel):
    code: str
    message: str
    severity: str
    details: Dict[str, Any] = Field(default_factory=dict)

class DialogueSegment(BaseModel):
    speaker: str
    text: str
    confidence: float

class Claim(BaseModel):
    claim: str
    type: str
    confidence: float
    source_span: str

class ExtractionData(BaseModel):
    translated_text: str
    structured_dialogue: List[DialogueSegment]
    claims_by_creator: List[Claim]

class ClaimExtractionResult(BaseModel):
    status: str
    errors: List[ErrorDetail]
    meta: Dict[str, Any]
    data: ExtractionData

_agent: Optional[Agent] = None

def get_agent() -> Agent:
    global _agent
    if _agent is None:
        logger.info("Initializing Claim Extraction Agent")
        _agent = Agent(
            name="ClaimExtractorAgent",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key,
                temperature=0.1
            ),
            description="You are a precise information extraction system that performs translation, speaker identification, and claim extraction in one pass.",
            instructions=[
                "CRITICAL: RETURN ONLY VALID JSON. NO TEXT OUTSIDE JSON.",
                "",
                "PROCESS TEXT IN THREE STEPS:",
                "",
                "STEP 1 - TRANSLATION:",
                "- Translate to English if not already English",
                "- Preserve meaning exactly, do not summarize",
                "- If already English, keep unchanged",
                "",
                "STEP 2 - SPEAKER IDENTIFICATION:",
                "- 'creator' = the person posting/narrating/reacting to the content",
                "- 'other' = any person quoted, shown, or referenced in the content",
                "- 'unknown' = when speaker is unclear",
                "- Split into meaningful dialogue segments",
                "",
                "STEP 3 - CLAIM EXTRACTION:",
                "- Extract ONLY claims made by 'creator'",
                "- A claim must be objectively verifiable (not pure opinion)",
                "- Each claim must be independent (no duplicates or merged ideas)",
                "- Include exact supporting span from source text",
                "- Ignore: opinions, emotional statements, rhetorical questions",
                "- Type: 'factual' (verifiable), 'opinion' (subjective), 'unclear' (ambiguous)",
                "",
                "REQUIRED OUTPUT JSON STRUCTURE (ALL FIELDS MUST EXIST):",
                "{",
                '  "status": "success" | "partial_success" | "failure",',
                '  "errors": [',
                "    {",
                '      "code": "TRANSLATION_ERROR" | "SPEAKER_DETECTION_ERROR" | "CLAIM_EXTRACTION_ERROR" | "LOW_CONFIDENCE" | "INVALID_INPUT",',
                '      "message": "string describing the error",',
                '      "severity": "warning" | "critical",',
                '      "details": {}',
                "    }",
                "  ],",
                '  "meta": {',
                '    "input_language": "detected language",',
                '    "confidence": 0.0 to 1.0,',
                '    "notes": "additional notes"',
                "  },",
                '  "data": {',
                '    "translated_text": "full translated text",',
                '    "structured_dialogue": [',
                "      {",
                '        "speaker": "creator" | "other" | "unknown",',
                '        "text": "exact spoken text",',
                '        "confidence": 0.0 to 1.0',
                "      }",
                "    ],",
                '    "claims_by_creator": [',
                "      {",
                '        "claim": "the claim statement",',
                '        "type": "factual" | "opinion" | "unclear",',
                '        "confidence": 0.0 to 1.0,',
                '        "source_span": "exact text from input"',
                "      }",
                "    ]",
                "  }",
                "}",
                "",
                "ERROR HANDLING:",
                "- If input is empty/meaningless: return status='failure' with INVALID_INPUT error",
                "- If translation fails: add TRANSLATION_ERROR, return partial_success",
                "- If speaker detection fails: add SPEAKER_DETECTION_ERROR, continue with best effort",
                "- If any confidence < 0.6: add LOW_CONFIDENCE warning, set status='partial_success'",
                "- If steps succeed but with warnings: status='partial_success'",
                "- If all steps complete successfully: status='success'",
                "",
                "CONFIDENCE RULES:",
                "- confidence must be float between 0.0 and 1.0 for every segment and claim",
                "- Set lower confidence if you are uncertain",
                "- If confidence < 0.6, include LOW_CONFIDENCE error",
                "",
                "MANDATORY:",
                "- Return ONLY valid JSON matching the structure above",
                "- ALL fields must be present",
                "- NO explanations, NO markdown, NO extra text",
                "- structured_dialogue must be an array (can be empty)",
                "- claims_by_creator must be an array (can be empty if no claims found)",
                "- errors must be an array (can be empty if no errors)",
            ],
        )
    return _agent

async def extract_claims(transcribed_text: str) -> ClaimExtractionResult:
    logger.info("Starting claim extraction")
    
    if not transcribed_text or not transcribed_text.strip():
        logger.error("Input text is empty")
        return ClaimExtractionResult(
            status="failure",
            errors=[ErrorDetail(
                code="INVALID_INPUT",
                message="Input text is empty or whitespace only",
                severity="critical"
            )],
            meta={
                "input_language": "unknown",
                "confidence": 0.0,
                "notes": "Input validation failed"
            },
            data=ExtractionData(
                translated_text="",
                structured_dialogue=[],
                claims_by_creator=[]
            )
        )
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting extraction (attempt {retry_count + 1}/{max_retries})")
            agent = get_agent()
            response = await agent.arun(f"Extract claims from this text:\n\n{transcribed_text}")
            
            if not response or not response.content:
                logger.warning(f"Empty response from agent (attempt {retry_count + 1})")
                retry_count += 1
                continue
            
            response_text = response.content
            logger.debug(f"Raw LLM output: {response_text}")
            
            if isinstance(response_text, str):
                try:
                    result_json = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in response (attempt {retry_count + 1}): {str(e)}")
                    retry_count += 1
                    continue
            else:
                result_json = response_text
            
            validated = ClaimExtractionResult(**result_json)
            logger.info(f"Successfully extracted {len(validated.data.claims_by_creator)} claims")
            return validated
            
        except ValidationError as e:
            logger.warning(f"Schema validation failed (attempt {retry_count + 1}): {str(e)}")
            retry_count += 1
            continue
        except Exception as e:
            logger.error(f"Error during extraction (attempt {retry_count + 1}): {str(e)}", exc_info=True)
            retry_count += 1
            continue
    
    logger.error("All retry attempts failed")
    return ClaimExtractionResult(
        status="failure",
        errors=[ErrorDetail(
            code="CLAIM_EXTRACTION_ERROR",
            message="Failed to extract claims after multiple retry attempts",
            severity="critical"
        )],
        meta={
            "input_language": "unknown",
            "confidence": 0.0,
            "notes": "All LLM calls failed or returned invalid JSON"
        },
        data=ExtractionData(
            translated_text="",
            structured_dialogue=[],
            claims_by_creator=[]
        )
    )
