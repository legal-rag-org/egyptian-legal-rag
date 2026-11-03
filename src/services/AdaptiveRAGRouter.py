
import logging

from pydantic import BaseModel, ConfigDict, Field


class FeatureRouting(BaseModel):

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = Field(default=None)
    reason: str | None = Field(default=None)


class AdaptiveRAGRoutingPlan(BaseModel):

    model_config = ConfigDict(extra="forbid")

    query_rewriting: FeatureRouting | None = None
    multi_query: FeatureRouting | None = None
    hyde: FeatureRouting | None = None
    metadata_filtering: FeatureRouting | None = None


class AdaptiveRAGRouter:

    def __init__(self, generation_model, template_parser):
        self.generation_model = generation_model
        self.template_parser = template_parser
        self.logger = logging.getLogger(__name__)

    def _get_default_routing_plan(self) -> dict:
        return {
            "query_rewriting": {
                "enabled": True,
                "reason": "Router failed. Using default strategy."
            },
            "multi_query": {
                "enabled": True,
                "reason": "Router failed. Using default strategy."
            },
            "hyde": {
                "enabled": True,
                "reason": "Router failed. Using default strategy."
            },
            "metadata_filtering": {
                "enabled": True,
                "reason": "Router failed. Using default strategy."
            },
        }

    def _validate_routing_plan(self, routing_plan: dict) -> dict:
        default_plan = self._get_default_routing_plan()

        if not isinstance(routing_plan, dict):
            self.logger.warning("Invalid routing plan format.")
            return default_plan

        valid_plan = {}
        valid_features = 0

        for feature, default_config in default_plan.items():
            config = routing_plan.get(feature)

            if (
                isinstance(config, dict)
                and isinstance(config.get("enabled"), bool)
            ):
                reason = config.get("reason", "")

                if not isinstance(reason, str):
                    self.logger.warning(
                        "Invalid reason for feature: %s", feature
                    )
                    reason = ""

                valid_plan[feature] = {
                    "enabled": config["enabled"],
                    "reason": reason
                }

                valid_features += 1

            else:
                self.logger.warning(
                    "Invalid routing configuration for feature: %s",
                    feature
                )
                valid_plan[feature] = default_config

        if valid_features == 0:
            self.logger.warning(
                "No valid routing features found. Using default plan."
            )
            return default_plan

        return valid_plan

    async def route(
        self,
        query: str,
        conversation_context: str = ""
    ) -> dict:

        try:
            prompt = self.template_parser.get(
                group="rag",
                key="router_prompt",
                vars={
                    "query": query,
                    "conversation_context": conversation_context
                }
            )

            response = await self.generation_model.generate_structured(
                prompt=prompt,
                output_schema=AdaptiveRAGRoutingPlan
            )

            if response is None:
                self.logger.warning(
                    "Adaptive RAG Router returned None falling back to static rag pipeline"
                )
                return self._get_default_routing_plan()

            routing_plan = response.model_dump(exclude_none=True)

            return self._validate_routing_plan(routing_plan)

        except Exception:
            self.logger.exception("Adaptive RAG Router failed.")
            return self._get_default_routing_plan()
