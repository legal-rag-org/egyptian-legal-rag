from .LLMEnums import LLMEnums
from .providers.OpenAiProvider import OpenAiProvider
from .providers.CohereProvider import CohereProvider
from .providers.HuggingFaceProvider import HuggingFaceProvider
from .providers.SentenceTransformerProvider import SentenceTransformerProvider
from .providers.OpenRouterProvider import OpenRouterProvider
from .providers.GeminiProvider import GeminiProvider

class LLMProviderFactory:
    def __init__(self, config:dict):
        self.config = config


    def create(self, provider: str):

        if provider == LLMEnums.OPENAI.value:
            return OpenAiProvider(
                api_key = self.config.OPENAI_API_KEY,
                api_url = self.config.OPENAI_API_URL,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_output_max_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider == LLMEnums.COHERE.value:
            return CohereProvider(
                api_key = self.config.COHERE_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_output_max_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider == LLMEnums.HUGGINGFACE.value:
            return HuggingFaceProvider(
                 api_key=self.config.HUGGINGFACE_API_KEY,
                 default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                 default_input_max_character=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                 default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )
        
        if provider == LLMEnums.SENTENCE_TRANSFORMER.value:
            return SentenceTransformerProvider(
                default_input_max_character=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider == LLMEnums.OPEN_ROUTER.value:
            return OpenRouterProvider(
                api_key = self.config.OPENROUTER_API_KEY,
                api_url = self.config.OPENROUTER_BASE_URL,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_output_max_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
        )

        if provider == LLMEnums.GEMINI.value:
            return GeminiProvider(
                api_key = self.config.GEMINI_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_output_max_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
        )

        raise ValueError(f"Unsupported LLM provider: {provider}")

