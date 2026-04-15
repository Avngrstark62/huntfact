import json
from typing import Optional

from openai import OpenAI

from config import settings
from logging_config import get_logger
from .system_prompt_1 import EXTRACT_FACTCHECK_QUESTIONS_PROMPT

logger = get_logger("services.reasoning_model")


class ReasoningModel:
    def __init__(
        self,
        model_provider: str = None,
        model_name: str = None,
    ):
        self.model_provider = model_provider or settings.reasoning_model_provider
        self.model_name = model_name or settings.reasoning_model_name
        
        if self.model_provider == "openai":
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            error_msg = f"Unsupported model provider: {self.model_provider}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"ReasoningModel initialized with provider={self.model_provider}, model={self.model_name}")

    def extract_factcheck_questions(self, utterances: str) -> Optional[list[str]]:
        """
        Extract fact-checkable questions from utterances.
        
        Args:
            utterances: Text content from audio transcript
            
        Returns:
            List of questions for fact-checking, or None if extraction fails
        """
        try:
            prompt = EXTRACT_FACTCHECK_QUESTIONS_PROMPT.format(utterances=utterances)
            
            logger.info(f"Extracting fact-check questions from {len(utterances)} chars of utterances")
            
            response = self.client.messages.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            questions = json.loads(content)
            
            logger.info(f"Successfully extracted {len(questions)} questions")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            return None
        except Exception as e:
            error_msg = f"Error extracting questions: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return None
