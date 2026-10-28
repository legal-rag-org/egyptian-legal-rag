from ..LLMInterface import LLMInterface
from ..LLMEnums import OpenAIEnums
from openai import AsyncOpenAI
import logging
from typing import List, Union

class OpenAiProvider(LLMInterface):

    def __init__(self,
                 api_key: str,
                 api_url: str = None,
                 default_input_max_characters: int=1000,
                 default_generation_output_max_tokens: int=1000,
                 default_generation_temperature: float=0.1):

        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_output_max_tokens = default_generation_output_max_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
        )

        self.enums = OpenAIEnums
        self.logger = logging.getLogger("uvicorn.error")



    def set_generation_model(self, model_id: str):
            self.generation_model_id = model_id


    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size


    def process_text(self, text: str):

         return text.strip() if len(text) <= self.default_input_max_characters else text[:self.default_input_max_characters].strip()
    


    async def generate_text(self,
                          prompt: str,
                          chat_history: list | None = None,
                          max_output_tokens: int=None,
                          temperature: float= None):

        chat_history = list(chat_history or [])

        if not self.client:
            self.logger.error("OpenAi client was not set")
            return None
        
        if not self.generation_model_id:
            self.logger.error("Generation Model for OpenAi was not set")
            return None


        max_output_tokens = max_output_tokens if max_output_tokens is not None else self.default_generation_output_max_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature


        chat_history.append(
             self.construct_prompt(
                  prompt=prompt,
                  role=OpenAIEnums.USER.value
             )
        )

        response = await self.client.chat.completions.create(
             model=self.generation_model_id,
             messages=chat_history,
             max_tokens=max_output_tokens,
             temperature=temperature
        )

        if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
            self.logger.error("Error while generating text with OpenAI")
            return None

        return response.choices[0].message.content

    async def generate_with_image(
        self,
        prompt: str,
        image_base64: str,
        image_mime_type: str = "image/png",
        max_output_tokens: int = 4096,
    ):
        if not self.client or not self.generation_model_id:
            self.logger.error("OCR client or model was not configured")
            return None

        try:
            response = await self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": (
                                        f"data:{image_mime_type};base64,"
                                        f"{image_base64}"
                                    )
                                },
                            },
                        ],
                    }
                ],
                max_tokens=max_output_tokens,
                temperature=0.0,
            )

            if not response.choices:
                return None

            return response.choices[0].message.content

        except Exception:
            self.logger.exception("Error during OCR inference")
            return None

    async def generate_with_tools(
        self,
        messages: list,
        tools: list,
        max_output_tokens: int = None,
        temperature: float = None,
    ):

        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error(
                "Generation Model for OpenAI was not set"
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

        try:
            response = await self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=max_output_tokens,
                temperature=temperature,
            )

        except Exception as e:
            self.logger.error(
                f"Error while generating response with tools: {e}"
            )
            return None

        self.logger.info(
            f"OpenAI model used: {response.model}"
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


    async def embed_text(self,
                   text: Union[str, List[str]],
                   document_type: str=None):
            
        if not self.client:
                self.logger.error("OpenAi client was not set")
                return None

        if not self.embedding_model_id:
                self.logger.error("Embedding Model for OpenAi was not set")
                return None

        if isinstance(text, str):
            text = [text]

        response = await self.client.embeddings.create(
                model=self.embedding_model_id,
                input=text
        )

        if not response or not response.data or len(response.data) == 0 or not response.data[0].embedding:
            self.logger.error("Error while embedding text with OpenAI")
            return None

        return [rec.embedding for rec in response.data]

    

    def construct_prompt(self,
                        prompt: str,
                        role: str):

        return {
             "role" : role,
             "content" : prompt
        }

