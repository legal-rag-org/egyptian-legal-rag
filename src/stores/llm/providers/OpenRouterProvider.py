from ..LLMInterface import LLMInterface
from ..LLMEnums import OpenRouterEnum

from openai import AsyncOpenAI

import logging
from typing import List, Union, Type
from pydantic import BaseModel


class OpenRouterProvider(LLMInterface):

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://openrouter.ai/api/v1",
        default_input_max_characters: int = 1000,
        default_generation_output_max_tokens: int = 2048,
        default_generation_temperature: float = 0.1,
    ):

        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_output_max_tokens = (
            default_generation_output_max_tokens
        )
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
        )

        self.enums = OpenRouterEnum
        self.logger = logging.getLogger("uvicorn.error")

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(
        self,
        model_id: str,
        embedding_size: int,
    ):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):

        return (
            text.strip()
            if len(text) <= self.default_input_max_characters
            else text[:self.default_input_max_characters].strip()
        )

    async def generate_text(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int = None,
        temperature: float = None,
    ):

        if not self.client:
            raise RuntimeError("OpenRouter client was not set")

        if not self.generation_model_id:
            raise RuntimeError("Generation Model for OpenRouter was not set")

        chat_history = list(chat_history or [])

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_output_max_tokens
        )

        temperature = (
            temperature
            if temperature is not None
            else self.default_generation_temperature
        )

        chat_history.append(
            self.construct_prompt(
                prompt=prompt,
                role=OpenRouterEnum.USER.value,
            )
        )

        response = await self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature,
        )

        if not response or not response.choices:
            raise RuntimeError("Empty response from OpenRouter")

        message = response.choices[0].message

        if not message or not message.content:
            raise RuntimeError("OpenRouter returned empty text")

        self.logger.info(f"OpenRouter model used: {response.model}")

        return message.content

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Type[BaseModel],
        chat_history: list | None = None,
        max_output_tokens: int = None,
        temperature: float = None,
    ):
        if not self.client:
            raise RuntimeError("OpenRouter client was not set")

        if not self.generation_model_id:
            raise RuntimeError("Generation Model for OpenRouter was not set")

        chat_history = list(chat_history or [])

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_output_max_tokens
        )

        temperature = (
            temperature
            if temperature is not None
            else self.default_generation_temperature
        )

        chat_history.append(
            self.construct_prompt(
                prompt=prompt,
                role=OpenRouterEnum.USER.value,
            )
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=chat_history,
                max_tokens=max_output_tokens,
                temperature=temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": output_schema.__name__,
                        "strict": True,
                        "schema": output_schema.model_json_schema(),
                    },
                },
                extra_body={
                    "provider": {
                        "require_parameters": True,
                    }
                },
            )

            if not response or not response.choices:
                raise RuntimeError("Empty response from OpenRouter")

            choice = response.choices[0]
            message = choice.message

            if not message:
                raise RuntimeError("Empty message from OpenRouter")

            if choice.finish_reason == "length":
                raise RuntimeError(
                    "Structured output was truncated because max_output_tokens was reached"
                )

            if message.refusal:
                raise RuntimeError(
                    f"OpenRouter refused structured generation: {message.refusal}"
                )

            raw_output = message.content

            if not raw_output:
                raise RuntimeError("OpenRouter returned empty structured output")

            return output_schema.model_validate_json(raw_output)

        except Exception:
            self.logger.exception(
                "Error while generating structured output with OpenRouter"
            )
            raise

    async def generate_with_tools(
        self,
        messages: list,
        tools: list,
        max_output_tokens: int = None,
        temperature: float = None,
    ):

        if not self.client:
            raise RuntimeError("OpenRouter client was not set")

        if not self.generation_model_id:
            raise RuntimeError("Generation Model for OpenRouter was not set")

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_output_max_tokens
        )

        temperature = (
            temperature
            if temperature is not None
            else self.default_generation_temperature
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=max_output_tokens,
                temperature=temperature,
            )

            if not response or not response.choices:
                raise RuntimeError("Empty response from OpenRouter tools")

            message = response.choices[0].message

            if not message:
                raise RuntimeError("Empty message from OpenRouter tools")

            self.logger.info(f"OpenRouter model used: {response.model}")

            return message

        except Exception:
            self.logger.exception(
                "Error while generating response with OpenRouter tools"
            )
            raise
    
    

    async def embed_text(
        self,
        text: Union[str, List[str]],
        document_type: str = None,
    ):

        if not self.client:
            raise RuntimeError("OpenRouter client was not set")

        if not self.embedding_model_id:
            raise RuntimeError("Embedding Model for OpenRouter was not set")

        if isinstance(text, str):
            text = [text]

        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model_id,
                input=text,
            )

            if not response or not response.data:
                raise RuntimeError("Empty embedding response from OpenRouter")

            if any(not record.embedding for record in response.data):
                raise RuntimeError("Invalid embedding returned from OpenRouter")

            return [
                record.embedding
                for record in response.data
            ]

        except Exception:
            self.logger.exception(
                "Error while generating embeddings with OpenRouter"
            )
            raise

    def construct_prompt(
        self,
        prompt: str,
        role: str,
    ):

        return {
            "role": role,
            "content": prompt,
        }