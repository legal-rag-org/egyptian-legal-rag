
from typing import Any


class FallbackUnavailableError(Exception):
    """Raised when no compatible fallback provider is available."""


class FallbackHandler:

    def __init__(
        self,
        providers: dict[str, Any],
        fallback_order: dict[str, list[str]],
        provider_capabilities: dict[str, set[str]]
    ):
        self.providers = providers
        self.fallback_order = fallback_order
        self.provider_capabilities = provider_capabilities

    def get_fallback_provider(
        self,
        primary_provider: str,
        operation: str
    ) -> tuple[str, Any]:

        candidates = self.fallback_order.get(operation, [])

        for provider_name in candidates:

            # Don't select the primary provider again
            if provider_name == primary_provider:
                continue

            # Check whether provider exists
            provider = self.providers.get(provider_name)

            if provider is None:
                continue

            # Check whether provider supports the operation
            capabilities = self.provider_capabilities.get(
                provider_name,
                set()
            )

            if operation not in capabilities:
                continue

            return provider_name, provider

        raise FallbackUnavailableError(
            f"No compatible fallback provider found for: {operation}"
        )

    
    def get_fallback_providers(
        self,
        primary_provider: str,
        operation: str
    ) -> list[tuple[str, Any]]:

        candidates = self.fallback_order.get(operation, [])
        available = []

        for provider_name in candidates:

            if provider_name == primary_provider:
                continue

            provider = self.providers.get(provider_name)

            if provider is None:
                continue

            capabilities = self.provider_capabilities.get(
                provider_name,
                set()
            )

            if operation in capabilities:
                available.append((provider_name, provider))

        return available

