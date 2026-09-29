import logging
from sentence_transformers import SentenceTransformer
from ..LLMInterface import LLMInterface
from ..LLMEnums import DocumentTypeEnum
from typing import List, Union

class SentenceTransformerProvider(LLMInterface):

    def __init__(self, default_input_max_character: int = 1024,
                 default_generation_max_output_tokens: int = 200,
                 temperature: float = 0.1):

        self.default_input_max_character = default_input_max_character
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.temperature = temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        self.embedding_client = None

        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        # sentence-transformers provider is embedding-only in this project
        raise NotImplementedError

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self.embedding_client = SentenceTransformer(self.embedding_model_id)

    def process_text(self, text: str):
                if len(text) < self.default_input_max_character:
                        return text.strip()
                
                return text[:self.default_input_max_character].strip()

    
    def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: int = None,
                       temperature: float = None):
        
        raise NotImplementedError
    

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if self.embedding_client is None or self.embedding_model_id is None:
            self.logger.error(
                "Embedding model for SentenceTransformerProvider was not set"
            )
            return None

        is_single_text = isinstance(text, str)

        if is_single_text:
            text = [text]

        embedding = self.embedding_client.encode(
            text,
            convert_to_numpy=True
        )

        embedding = embedding.tolist()

        if is_single_text:
            return embedding[0]

        return embedding

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}

    def generate_with_tools(
            self,
            messages: list,
            tools: list,
            max_output_tokens: int = None,
            temperature: float = None,
        ):
            pass

    