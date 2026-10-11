from ..LLMInterface import LLMInterface
from stores.llm.LLMEnums import HuggingfaceEnum
from huggingface_hub import InferenceClient
import logging
from typing import List, Union

class HuggingFaceProvider(LLMInterface):
     def __init__(self, api_key: str, default_input_max_character: int=1024,
                                         default_generation_max_output_tokens: int=1000,
                                         temperature: float=0.1):

          self.api_key = api_key

          self.default_input_max_character = default_input_max_character
          self.default_generation_max_output_tokens = default_generation_max_output_tokens
          self.temperature = temperature
          
          self.generation_model_id = None
          self.embedding_model_id  = None
          self.embedding_size = None

          self.client = InferenceClient(
              api_key=self.api_key,
              )

          self.enums = HuggingfaceEnum
          self.logger = logging.getLogger(__name__)

     def set_generation_model(self, model_id: str):
            self.generation_model_id = model_id


     def set_embedding_model(self, model_id: str, embedding_size: int):
            self.embedding_model_id = model_id
            self.embedding_size = embedding_size


     def process_text(self, text: str):
            if len(text) < self.default_input_max_character:
                    return text.strip()
            
            return text[:self.default_input_max_character].strip()

     def generate_text(self, prompt: str, chat_history: list=[], max_output_tokens: int = None,
                          temperature: float = None):

            if not self.client:
                  self.logger.error("The HuggingFace client was not set")
                  return None
            if not self.generation_model_id:
                  self.logger.error("The Generation model for HuggingFace was not set")
                  return None

            if temperature is None:
                  temperature = self.temperature

            if max_output_tokens is None:
                  max_output_tokens = self.default_generation_max_output_tokens

            messages = []

            # add previous conversations
            if chat_history:
                  messages.extend(chat_history)

            # add current user prompt
            messages.append(self.construct_prompt(prompt=prompt, role=HuggingfaceEnum.USER.value))

            response = self.client.chat.completions.create(
                   model=self.generation_model_id,
                   messages=messages,
                   max_tokens=max_output_tokens,
                   temperature=temperature
            )

            if not response or not response.choices or not len(response.choices) == 0 or not response.choices[0].message:
                   self.logger.error("Error while generating text with HuggingFace")
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
              self.logger.error(
              "The HuggingFace client was not set"
              )
              return None

       if not self.generation_model_id:
              self.logger.error(
              "The Generation model for HuggingFace was not set"
              )
              return None

       if temperature is None:
              temperature = self.temperature

       if max_output_tokens is None:
              max_output_tokens = (
              self.default_generation_max_output_tokens
              )

       try:

              response = self.client.chat.completions.create(
              model=self.generation_model_id,
              messages=messages,
              tools=tools,
              tool_choice="auto",
              max_tokens=max_output_tokens,
              temperature=temperature,
              )

       except Exception as e:

              self.logger.error(
              f"Error while generating response with HuggingFace: {e}"
              )

              return None

       self.logger.info(
              f"HuggingFace model used: {self.generation_model_id}"
       )

       if (
              not response
              or not response.choices
              or not response.choices[0].message
       ):

              self.logger.error(
              "Error while generating response with HuggingFace"
              )

              return None

       return response.choices[0].message
     

     def embed_text(self, text: Union[str, List[str]], document_type: str = None):      
            if not self.client:
                   self.logger.error("The HuggingFace client was not set")
                   return None

            if not self.embedding_model_id:
                   self.logger.error("Embedding model for HuggingFace was not set")
                   return None

            if isinstance(text, str):
                   text = [text] 
            
            response = self.client.feature_extraction(
                text=text,
                model=self.embedding_model_id
            )

            if response is None:
                self.logger.error("Error while embedding text with Hugging Face")
                return None

            return response
                   
                     



     def construct_prompt(self, prompt: str, role: str):
                        return {
                            "role": role,
                            "content": prompt
                        }
                    