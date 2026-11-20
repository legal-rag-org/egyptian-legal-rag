from stores.llm.LLMResilienceService import LLMResilienceService

from stores.llm.resilience.retry_handler import RetryHandler
from stores.llm.resilience.fallback_handler import FallbackHandler
from stores.llm.resilience.resilience_config import (
    ResilienceConfig,
    RetryConfig,
)


class LLMResilienceFactory:

    def __init__(self, provider_factory, settings):
        self.provider_factory = provider_factory
        self.settings = settings

    def _create_provider(self, backend, model, client_type):

        provider = self.provider_factory.create(
            provider=backend
        )

        if provider is None:
            raise ValueError(
                f"Unsupported LLM provider: {backend}"
            )

        if client_type == "generation":
            provider.set_generation_model(model)

        elif client_type == "embedding":
            provider.set_embedding_model(
                model_id=model,
                embedding_size=self.settings.EMBEDDING_MODEL_SIZE,
            )

        else:
            raise ValueError(
                f"Unsupported client type: {client_type}"
            )

        return provider

    
    def _parse_fallbacks(self, fallbacks):

        parsed = []

        if not fallbacks:
            return parsed

        for index, item in enumerate(fallbacks.split(","), start=1):

            item = item.strip()

            if not item:
                continue

            parts = item.split(":", 2)

            if len(parts) == 2:
                # Backward compatibility:
                # GEMINI:model-name

                backend, model = parts
                instance_id = f"{backend.strip()}_FALLBACK_{index}"

            elif len(parts) == 3:
                # New format:
                # INSTANCE_ID:BACKEND:MODEL

                instance_id, backend, model = parts

            else:
                raise ValueError(
                    f"Invalid fallback configuration: {item}"
                )

            instance_id = instance_id.strip()
            backend = backend.strip()
            model = model.strip()

            if not instance_id or not backend or not model:
                raise ValueError(
                    f"Invalid fallback configuration: {item}"
                )

            parsed.append(
                (instance_id, backend, model)
            )

        return parsed


    
    def create(
        self,
        backend: str,
        model: str,
        fallbacks: str,
        client_type: str,
    ):

        # 1. Create primary provider

        primary_provider_id = f"{backend}_PRIMARY"

        primary_provider = self._create_provider(
            backend=backend,
            model=model,
            client_type=client_type,
        )

        # 2. Create fallback providers

        fallback_providers = {}

        parsed_fallbacks = self._parse_fallbacks(
            fallbacks
        )

        for (
            fallback_instance_id,
            fallback_backend,
            fallback_model
        ) in parsed_fallbacks:

            if fallback_instance_id == primary_provider_id:
                raise ValueError(
                    f"Fallback instance ID conflicts with primary: "
                    f"{fallback_instance_id}"
                )

            if fallback_instance_id in fallback_providers:
                raise ValueError(
                    f"Duplicate fallback instance ID: "
                    f"{fallback_instance_id}"
                )

            provider = self._create_provider(
                backend=fallback_backend,
                model=fallback_model,
                client_type=client_type,
            )

            fallback_providers[fallback_instance_id] = provider

        # 3. Configure operation capabilities

        operation_capabilities = {
            "generation": {
                "generate_text",
                "generate_structured",
                "generate_with_tools",
            },
            "embedding": {
                "embed_text",
            },
        }

        provider_capabilities = {
            instance_id: operation_capabilities[client_type]
            for instance_id in fallback_providers
        }

        fallback_order = {
            operation: list(fallback_providers.keys())
            for operation in operation_capabilities[client_type]
        }

        # 4. Create handlers

        fallback_handler = FallbackHandler(
            providers=fallback_providers,
            fallback_order=fallback_order,
            provider_capabilities=provider_capabilities,
        )

        retry_config = RetryConfig(
            max_attempts=self.settings.LLM_MAX_ATTEMPTS,
            initial_delay=self.settings.LLM_INITIAL_RETRY_DELAY,
            max_delay=self.settings.LLM_MAX_RETRY_DELAY,
            exponential_base=self.settings.LLM_EXPONENTIAL_BASE,
        )

        resilience_config = ResilienceConfig(
            timeout=self.settings.LLM_TIMEOUT,
            retry=retry_config,
        )

        retry_handler = RetryHandler(
            config=resilience_config
        )

        # 5. Return resilient client
        return LLMResilienceService(
            primary_provider=primary_provider,
            primary_provider_name=primary_provider_id,
            retry_handler=retry_handler,
            fallback_handler=fallback_handler,
        )