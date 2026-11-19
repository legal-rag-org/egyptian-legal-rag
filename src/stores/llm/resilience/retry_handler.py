import asyncio
import logging
import random

from typing import Callable, Awaitable, TypeVar

from .error_classifier import ErrorClassifier
from .resilience_config import ResilienceConfig

from utils.llm_metrics import LLM_RETRIES


T = TypeVar("T")


class RetryHandler:

    def __init__(self, config: ResilienceConfig):
        self.config = config
        self.logger = logging.getLogger("uvicorn.error")

    async def execute(
        self,
        operation: Callable[..., Awaitable[T]],
        *args,
        provider_name: str = "unknown",
        **kwargs
    ) -> T:

        retry_config = self.config.retry
        last_error = None

        for attempt in range(retry_config.max_attempts):

            try:
                return await operation(*args, **kwargs)

            except Exception as error:

                last_error = error

                classification = ErrorClassifier.classify(error)

                # Stop if error is not retryable
                if not classification.is_retryable:
                    self.logger.warning(
                        "Non-retryable error: %s",
                        classification.error_type.value
                    )
                    raise

                # Stop if maximum attempts reached
                if attempt == retry_config.max_attempts - 1:
                    self.logger.error(
                        "Maximum retry attempts reached."
                    )
                    raise

                # Exponential backoff
                exponential_delay = (
                    retry_config.initial_delay
                    * retry_config.exponential_base ** attempt
                )

                delay_cap = min(
                    exponential_delay,
                    retry_config.max_delay
                )

                # Full Jitter
                delay = random.uniform(0, delay_cap)

                self.logger.warning(
                    "Attempt %s failed. Retrying in %.2f seconds. Error: %s",
                    attempt + 1,
                    delay,
                    classification.error_type.value
                )

                LLM_RETRIES.labels(
                    provider=provider_name,
                    error_type=classification.error_type.value
                ).inc()

                await asyncio.sleep(delay)

        raise last_error
