import time
import logging

from .LLMInterface import LLMInterface
from .resilience.retry_handler import RetryHandler
from .resilience.fallback_handler import FallbackHandler
from .resilience.error_classifier import ErrorClassifier

from utils.llm_metrics import (
    LLM_PROVIDER_CALLS,
    LLM_PROVIDER_DURATION,
    LLM_FALLBACKS,
)

from typing import Type
from pydantic import BaseModel



class LLMResilienceService(LLMInterface):

    def __init__(
        self,
        primary_provider: LLMInterface,
        primary_provider_name: str,
        retry_handler: RetryHandler,
        fallback_handler: FallbackHandler,
    ):
        self.primary_provider = primary_provider
        self.primary_provider_name = primary_provider_name

        self.retry_handler = retry_handler
        self.fallback_handler = fallback_handler

        self.enums = self.primary_provider.enums
        self.embedding_size = self.primary_provider.embedding_size

        self.logger = logging.getLogger("uvicorn.error")

    async def _execute_provider(
        self,
        provider,
        provider_name: str,
        operation: str,
        *args,
        **kwargs
    ):
        start_time = time.perf_counter()

        try:
            result = await self.retry_handler.execute(
                getattr(provider, operation),
                *args,
                provider_name=provider_name,
                **kwargs
            )

            LLM_PROVIDER_CALLS.labels(
                provider=provider_name,
                operation=operation,
                outcome="success",
            ).inc()

            return result

        except Exception:
            LLM_PROVIDER_CALLS.labels(
                provider=provider_name,
                operation=operation,
                outcome="error",
            ).inc()

            raise

        finally:
            duration = time.perf_counter() - start_time

            LLM_PROVIDER_DURATION.labels(
                provider=provider_name,
                operation=operation,
            ).observe(duration)

    
    async def _execute(self, operation: str, *args, **kwargs):

        last_error = None

        # 1. Try primary provider
        try:
            return await self._execute_provider(
                provider=self.primary_provider,
                provider_name=self.primary_provider_name,
                operation=operation,
                *args,
                **kwargs
            )

        except Exception as primary_error:

            last_error = primary_error

            classification = ErrorClassifier.classify(
                primary_error
            )

            self.logger.warning(
                "Primary provider failed: provider=%s, operation=%s, "
                "error_type=%s, retryable=%s, should_fallback=%s",
                self.primary_provider_name,
                operation,
                classification.error_type.value,
                classification.is_retryable,
                classification.should_fallback,
            )

            if not classification.should_fallback:
                raise

        # 2. Get compatible fallback providers
        fallback_providers = (
            self.fallback_handler.get_fallback_providers(
                primary_provider=self.primary_provider_name,
                operation=operation
            )
        )

        self.logger.info(
            "Available fallback providers: %s",
            [name for name, _ in fallback_providers]
        )



        # 3. Try fallback providers
        for provider_name, provider in fallback_providers:

            LLM_FALLBACKS.labels(
                primary_provider=self.primary_provider_name,
                fallback_provider=provider_name,
                operation=operation,
            ).inc()

            self.logger.info(
                "Attempting fallback: primary=%s fallback=%s operation=%s",
                self.primary_provider_name,
                provider_name,
                operation
            )

            try:
                result = await self._execute_provider(
                    provider=provider,
                    provider_name=provider_name,
                    operation=operation,
                    *args,
                    **kwargs
                )

                self.logger.info(
                    "Fallback succeeded: provider=%s operation=%s",
                    provider_name,
                    operation
                )

                return result

            except Exception as fallback_error:

                last_error = fallback_error

                classification = ErrorClassifier.classify(
                    fallback_error
                )

                self.logger.warning(
                    "Fallback provider failed: provider=%s, operation=%s, "
                    "error_type=%s, retryable=%s, should_fallback=%s",
                    provider_name,
                    operation,
                    classification.error_type.value,
                    classification.is_retryable,
                    classification.should_fallback,
                )

                if not classification.should_fallback:
                    raise

        raise last_error


    def set_generation_model(self, model_id: str):
        self.primary_provider.set_generation_model(model_id)

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.primary_provider.set_embedding_model(
            model_id,
            embedding_size
        )

        self.embedding_size = embedding_size

    async def generate_text(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int = None,
        temperature: float = None
    ):
        return await self._execute(
            "generate_text",
            prompt=prompt,
            chat_history=chat_history,
            max_output_tokens=max_output_tokens,
            temperature=temperature
        )

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[BaseModel],
        chat_history: list | None = None,
        max_output_tokens: int = None,
        temperature: float = None
    ):
        return await self._execute(
            "generate_structured",
            prompt=prompt,
            output_schema=output_schema,
            chat_history=chat_history,
            max_output_tokens=max_output_tokens,
            temperature=temperature
        )

    async def generate_with_tools_detailed(
        self,
        messages: list,
        tools: list,
        max_output_tokens: int = None,
        temperature: float = None,
    ):
        return await self._execute(
            "generate_with_tools_detailed",
            messages=messages,
            tools=tools,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

    async def generate_with_tools(
        self,
        messages: list,
        tools: list,
        max_output_tokens: int = None,
        temperature: float = None
    ):
        return await self._execute(
            "generate_with_tools",
            messages=messages,
            tools=tools,
            max_output_tokens=max_output_tokens,
            temperature=temperature
        )

    async def embed_text(self, text: str, document_type: str = None):
        return await self._execute(
            "embed_text",
            text=text,
            document_type=document_type
        )

    def construct_prompt(self, prompt: str, role: str):
        return self.primary_provider.construct_prompt(
            prompt,
            role
        )
