from ..LLMInterface import LLMInterface
from ..LLMEnums import OpenRouterEnum

from openai import OpenAI

import logging
from typing import List, Union


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

        self.client = OpenAI(
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

    def generate_text(
        self,
        prompt: str,
        chat_history: list = None,
        max_output_tokens: int = None,
        temperature: float = None,
    ):

        if not self.client:
            self.logger.error("OpenRouter client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error(
                "Generation Model for OpenRouter was not set"
            )
            return None

        if chat_history is None:
            chat_history = []

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens
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

        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature,
        )
        self.logger.info(
            f"OpenRouter model used: {response.model}"
        )

        if (
            not response
            or not response.choices
            or len(response.choices) == 0
            or not response.choices[0].message
        ):
            self.logger.error(
                "Error while generating text with OpenRouter"
            )
            return None

        return response.choices[0].message.content

    def generate_with_tools(
        self,
        messages: list,
        tools: list,
        max_output_tokens: int = None,
        temperature: float = None,
    ):

        if not self.client:
            self.logger.error("OpenRouter client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error(
                "Generation Model for OpenRouter was not set"
            )
            return None

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

        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=max_output_tokens,
            temperature=temperature,
        )

        self.logger.info(
            f"OpenRouter model used: {response.model}"
        )

        if (
            not response
            or not response.choices
            or not response.choices[0].message
        ):
            self.logger.error(
                "Error while generating response with tools"
            )
            return None

        return response.choices[0].message

    def embed_text(
        self,
        text: Union[str, List[str]],
        document_type: str = None,
    ):

        if not self.client:
            self.logger.error("OpenRouter client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error(
                "Embedding Model for OpenRouter was not set"
            )
            return None

        if isinstance(text, str):
            text = [text]

        response = self.client.embeddings.create(
            model=self.embedding_model_id,
            input=text,
        )

        if (
            not response
            or not response.data
            or len(response.data) == 0
            or not response.data[0].embedding
        ):
            self.logger.error(
                "Error while embedding text with OpenRouter"
            )
            return None

        return [
            record.embedding
            for record in response.data
        ]

    def construct_prompt(
        self,
        prompt: str,
        role: str,
    ):

        return {
            "role": role,
            "content": prompt,
        }