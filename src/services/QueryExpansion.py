
import logging

from pydantic import BaseModel, ConfigDict, Field


class QueryExpansionResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    expanded_queries: list[str] = Field(
        description="Alternative search queries preserving the original query's intent."
    )


class QueryExpansion:

    def __init__(self, generation_model, template_parser):

        self.generation_model = generation_model
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")

    async def expand(self, rewritten_query: str) -> list[str]:

        query_expansion_prompt = self.template_parser.get(
            group="rag",
            key="query_expansion_prompt",
            vars={
                "query": rewritten_query
            }
        )

        try:
            response = await self.generation_model.generate_structured(
                prompt=query_expansion_prompt,
                output_schema=QueryExpansionResponse
            )

            if response is None:
                self.logger.warning(
                    "Query expansion returned None. "
                    "Falling back to rewritten query."
                )
                return [rewritten_query]

            expanded_queries = [
                query.strip()
                for query in response.expanded_queries
                if isinstance(query, str) and query.strip()
            ]

            expanded_queries = list(dict.fromkeys(expanded_queries))

            if not expanded_queries:
                self.logger.warning(
                    "Query expansion returned empty queries. "
                    "Falling back to rewritten query."
                )
                return [rewritten_query]

            return list(dict.fromkeys([
                rewritten_query,
                *expanded_queries
            ]))

        except Exception:
            self.logger.exception(
                "Query expansion error. "
                "Falling back to rewritten query."
            )

            return [rewritten_query]
