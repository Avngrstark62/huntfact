from openai import OpenAI
from typing import Type, TypeVar
from pydantic import BaseModel

from config import settings
from logging_config import get_logger

logger = get_logger("llm")

T = TypeVar('T', bound=BaseModel)


class LLM:
    """LLM wrapper for calling OpenAI models."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    def _log_usage(self, model: str, usage):
        """Log token usage and response details if debug is enabled."""
        print(f"DEBUG CHECK: llm_debug={settings.llm_debug}")
        
        if not settings.llm_debug:
            return
        
        logger.info(
            f"LLM Call Details:\n"
            f"  Model: {model}\n"
            f"  Prompt tokens: {usage.prompt_tokens}\n"
            f"  Completion tokens: {usage.completion_tokens}\n"
            f"  Total tokens: {usage.total_tokens}"
        )
    
    async def call(
        self,
        model: str,
        messages: list,
    ) -> str:
        """
        Call OpenAI model and return text response.
        
        Args:
            model: Model name (e.g., "gpt-4o-mini", "gpt-5-nano")
            messages: List of message dicts with "role" and "content"
        
        Returns:
            Model response as string
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            
            self._log_usage(model, response.usage)
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}", exc_info=True)
            raise
    
    async def call_with_schema(
        self,
        model: str,
        messages: list,
        schema_model: Type[T],
    ) -> T:
        """
        Call OpenAI model with Pydantic schema enforcement.
        
        Uses structured outputs to ensure response adheres to schema.
        
        Args:
            model: Model name (e.g., "gpt-4o-mini")
            messages: List of message dicts
            schema_model: Pydantic model for response structure
        
        Returns:
            Parsed response as schema_model instance
        """
        try:
            response = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema_model,
            )
            
            self._log_usage(model, response.usage)
            
            return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"LLM schema call failed: {str(e)}", exc_info=True)
            raise


# ✅ singleton instance
llm = LLM()

