from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field
from config import settings
from typing import Optional, List
from logging_config import get_logger
import json

logger = get_logger("agents.reasoning_agent")


class VerifiedClaim(BaseModel):
    claim: str = Field(..., description="The claim being made")
    verdict: str = Field(..., description="Verdict: VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, or FALSE")
    confidence: float = Field(..., description="Confidence level 0.0 to 1.0")
    explanation: str = Field(..., description="Explanation of the verification")


class VideoAnalysisResult(BaseModel):
    overall_verdict: str = Field(
        ...,
        description="Overall verdict: ACCURATE, MOSTLY_ACCURATE, MISLEADING, MISINTERPRETS_FACTS, SELECTIVE, or INACCURATE"
    )
    confidence: float = Field(..., description="Confidence in the overall verdict 0.0 to 1.0")
    summary: str = Field(..., description="Summary of the video's truthfulness")
    detailed_analysis: str = Field(..., description="Detailed reasoning about the claims and the video")
    verified_count: int = Field(..., description="Number of verified claims")
    false_count: int = Field(..., description="Number of false claims")
    unverified_count: int = Field(..., description="Number of unverified claims")


_reasoning_agent: Optional[Agent] = None


def get_agent() -> Agent:
    global _reasoning_agent
    if _reasoning_agent is None:
        logger.info("Initializing Reasoning Agent")
        _reasoning_agent = Agent(
            name="ReasoningAgent",
            model=Gemini(
                id="gemini-3-flash-preview",
                api_key=settings.google_api_key,
                temperature=0.3
            ),
            description="You are an expert fact-checker and critical analyst that evaluates videos for truthfulness and accuracy based on transcribed content and verified claims.",
            instructions=[
                "CRITICAL: RETURN ONLY VALID JSON. NO TEXT OUTSIDE JSON.",
                "",
                "YOU WILL RECEIVE:",
                "1. Transcribed text from a video (dialogue, statements, claims)",
                "2. A list of claims made in the video with their verification status (VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, FALSE)",
                "",
                "YOUR TASK:",
                "Analyze the video content and verified claims to determine the overall truthfulness of the video.",
                "",
                "VERDICTS YOU CAN ASSIGN:",
                "- ACCURATE: All major claims are verified as true, no false information",
                "- MOSTLY_ACCURATE: Majority of claims verified, minor issues or unverified aspects",
                "- MISLEADING: Mix of true and false claims, selective use of facts",
                "- MISINTERPRETS_FACTS: Claims are presented but misinterpret or distort factual information",
                "- SELECTIVE: Uses true facts but selectively presents them to create false impression",
                "- INACCURATE: Most or all claims are false or heavily contradicted by evidence",
                "",
                "REASONING PROCESS:",
                "1. Count verified claims, false claims, unverified claims",
                "2. Identify patterns: are false claims critical to the argument or peripheral?",
                "3. Check for selective reporting: are true facts presented in misleading context?",
                "4. Look for logical consistency: does the narrative make sense or distort information?",
                "5. Assess intent: is this misinformation, misunderstanding, or selective presentation?",
                "",
                "BIAS PREVENTION:",
                "- Base your verdict ONLY on the verification results, NOT on ideology",
                "- Do not favor or disfavor claims based on political/cultural viewpoint",
                "- If claims are verified, they are true regardless of topic",
                "- If claims are false, they are false regardless of topic",
                "- Use the same standards for all types of content",
                "- If you find yourself drawn to one conclusion, critically examine why",
                "",
                "OUTPUT JSON STRUCTURE (ALL FIELDS MUST EXIST):",
                "{",
                '  "overall_verdict": "ACCURATE" | "MOSTLY_ACCURATE" | "MISLEADING" | "MISINTERPRETS_FACTS" | "SELECTIVE" | "INACCURATE",',
                '  "confidence": 0.0 to 1.0,',
                '  "summary": "one sentence summary of the video truthfulness",',
                '  "detailed_analysis": "detailed reasoning about claims, patterns, and the overall verdict",',
                '  "verified_count": number,',
                '  "false_count": number,',
                '  "unverified_count": number',
                "}",
                "",
                "IMPORTANT GUIDELINES:",
                "- confidence should reflect certainty in the verdict based on claim verification data",
                "- detailed_analysis should explain the reasoning, not just list claims",
                "- Be objective and data-driven in your analysis",
                "- Return ONLY valid JSON matching the structure above",
                "- NO explanations, NO markdown, NO extra text",
            ],
        )
    return _reasoning_agent


async def analyze_video(transcribed_text: str, verified_claims: List[VerifiedClaim]) -> VideoAnalysisResult:
    """
    Analyze video content and verified claims to determine overall truthfulness.
    
    Args:
        transcribed_text: The transcribed text from the video
        verified_claims: List of claims with their verification results
    
    Returns:
        VideoAnalysisResult with overall verdict and detailed analysis
    """
    logger.info(f"Starting video analysis with {len(verified_claims)} verified claims")
    
    if not transcribed_text or not transcribed_text.strip():
        logger.error("Input text is empty")
        return VideoAnalysisResult(
            overall_verdict="UNVERIFIED",
            confidence=0.0,
            summary="Unable to analyze video: transcribed text is empty",
            detailed_analysis="No transcribed text provided for analysis",
            verified_count=0,
            false_count=0,
            unverified_count=0
        )
    
    claims_text = "\n".join([
        f"- Claim: {claim.claim}\n  Verdict: {claim.verdict}\n  Confidence: {claim.confidence}\n  Explanation: {claim.explanation}"
        for claim in verified_claims
    ])
    
    formatted_input = f"""
TRANSCRIBED VIDEO TEXT:
-----------------------
{transcribed_text}

-----------------------

VERIFIED CLAIMS:
-----------------------
{claims_text if claims_text else "No claims provided"}

-----------------------

Please analyze this video content based on the verified claims and provide your assessment of the overall truthfulness of the video. Focus on patterns, consistency, selective reporting, and whether the video is accurate, misleading, or misrepresents facts. Base your verdict strictly on the verification data, not on your personal biases or ideological preferences.
"""
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting analysis (attempt {retry_count + 1}/{max_retries})")
            agent = get_agent()
            response = await agent.arun(formatted_input)
            
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
            
            validated = VideoAnalysisResult(**result_json)
            logger.info(f"Successfully analyzed video with verdict: {validated.overall_verdict}")
            return validated
            
        except Exception as e:
            logger.warning(f"Error during analysis (attempt {retry_count + 1}): {str(e)}")
            retry_count += 1
            continue
    
    logger.error("All retry attempts failed")
    return VideoAnalysisResult(
        overall_verdict="UNVERIFIED",
        confidence=0.0,
        summary="Unable to complete analysis due to processing error",
        detailed_analysis="All analysis attempts failed",
        verified_count=len([c for c in verified_claims if c.verdict == "VERIFIED"]),
        false_count=len([c for c in verified_claims if c.verdict == "FALSE"]),
        unverified_count=len([c for c in verified_claims if c.verdict == "UNVERIFIED"])
    )
