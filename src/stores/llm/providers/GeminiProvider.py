from ..LLMInterface import LLMInterface
from ..LLMEnums import GeminiEnums

from google import genai

import logging
from typing import List, Union


class GeminiProvider(LLMInterface):

    def __init__(
        self,
        api_key: str,
        default_input_max_characters: int = 1000,
        default_generation_output_max_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
    ):

        self.api_key = api_key

        self.default_input_max_characters = (
            default_input_max_characters
        )

        self.default_generation_output_max_tokens = (
            default_generation_output_max_tokens
        )

        self.default_generation_temperature = (
            default_generation_temperature
        )

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = genai.Client(
            api_key=self.api_key
        )

        self.enums = GeminiEnums
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
            else text[
                :self.default_input_max_characters
            ].strip()
        )

    def generate_text(
        self,
        prompt: str,
        chat_history: list = None,
        max_output_tokens: int = None,
        temperature: float = None,
    ):

        if not self.client:
            self.logger.error(
                "Gemini client was not set"
            )
            return None

        if not self.generation_model_id:
            self.logger.error(
                "Generation Model for Gemini was not set"
            )
            return None

        if chat_history is None:
            chat_history = []

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

        contents = []

        for message in chat_history:

            role = message.get("role")
            content = message.get("content")

            if role == GeminiEnums.SYSTEM.value:
                continue

            if role == GeminiEnums.USER.value:
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": content
                            }
                        ],
                    }
                )

            elif role == GeminiEnums.ASSISTANT.value:
                contents.append(
                    {
                        "role": "model",
                        "parts": [
                            {
                                "text": content
                            }
                        ],
                    }
                )

        contents.append(
            {
                "role": GeminiEnums.USER.value,
                "parts": [
                    {
                        "text": prompt
                    }
                ],
            }
        )

        response = self.client.models.generate_content(
            model=self.generation_model_id,
            contents=contents,
            config={
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
            },
        )

        if not response or not response.text:
            self.logger.error(
                "Error while generating text with Gemini"
            )
            return None

        return response.text

    def generate_with_tools(
        self,
        messages: list,
        tools: list,
        max_output_tokens: int = None,
        temperature: float = None,
    ):

        if not self.client:
            self.logger.error(
                "The Gemini client was not set"
            )
            return None

        if not self.generation_model_id:
            self.logger.error(
                "The Generation model for Gemini was not set"
            )
            return None

        if temperature is None:
            temperature = self.temperature

        if max_output_tokens is None:
            max_output_tokens = (
                self.default_generation_max_output_tokens
            )

        try:

            response = self.client.models.generate_content(
                model=self.generation_model_id,
                contents=messages,
                config={
                    "tools": tools,
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                },
            )

        except Exception as e:

            self.logger.error(
                f"Error while generating response with Gemini: {e}"
            )

            return None

        self.logger.info(
            f"Gemini model used: {self.generation_model_id}"
        )

        if (
            not response
            or not response.candidates
            or not response.candidates[0].content
        ):

            self.logger.error(
                "Error while generating response with Gemini"
            )

            return None

        return response.candidates[0].content

    def embed_text(
        self,
        text: Union[str, List[str]],
        document_type: str = None,
    ):

        if not self.client:
            self.logger.error(
                "Gemini client was not set"
            )
            return None

        if not self.embedding_model_id:
            self.logger.error(
                "Embedding Model for Gemini was not set"
            )
            return None

        if isinstance(text, str):
            text = [text]

        embeddings = []

        for item in text:

            response = self.client.models.embed_content(
                model=self.embedding_model_id,
                contents=item,
            )

            if (
                not response
                or not response.embeddings
                or len(response.embeddings) == 0
                or not response.embeddings[0].values
            ):
                self.logger.error(
                    "Error while embedding text with Gemini"
                )
                return None

            embeddings.append(
                response.embeddings[0].values
            )

        return embeddings

    def construct_prompt(
        self,
        prompt: str,
        role: str,
    ):

        return {
            "role": role,
            "content": prompt,
        }