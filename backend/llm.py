from openai import OpenAI
from typing import Type, TypeVar
from pydantic import BaseModel
import logging

from config import settings
from logging_config import get_logger, log_event

logger = get_logger("llm")

T = TypeVar('T', bound=BaseModel)


class LLM:
    """LLM wrapper for calling OpenAI models."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai.api_key)
    
    def _log_usage(self, model: str, usage):
        """Log token usage and response details if debug is enabled."""
        if not settings.llm.debug:
            return

        log_event(
            logger,
            level=logging.INFO,
            event="provider.request.succeeded",
            status="succeeded",
            message="LLM usage details",
            component="llm",
            provider="openai",
            operation="chat.completions",
            model=model,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
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
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.started",
                status="started",
                message="Starting LLM text call",
                component="llm",
                provider="openai",
                operation="chat.completions",
                model=model,
            )
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            
            self._log_usage(model, response.usage)
            
            return response.choices[0].message.content
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="LLM call failed",
                component="llm",
                provider="openai",
                operation="chat.completions",
                model=model,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
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
            log_event(
                logger,
                level=logging.INFO,
                event="provider.request.started",
                status="started",
                message="Starting LLM schema call",
                component="llm",
                provider="openai",
                operation="chat.completions.parse",
                model=model,
            )
            response = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema_model,
            )
            
            self._log_usage(model, response.usage)
            
            return response.choices[0].message.parsed
        except Exception as e:
            log_event(
                logger,
                level=logging.ERROR,
                event="provider.request.failed",
                status="failed",
                message="LLM schema call failed",
                component="llm",
                provider="openai",
                operation="chat.completions.parse",
                model=model,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            raise


# ✅ singleton instance
llm = LLM()

