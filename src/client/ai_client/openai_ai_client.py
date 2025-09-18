from openai import OpenAI, AsyncOpenAI
from random import choice

from .base_ai_client import BaseAIClient


class OpenaiAIClient(BaseAIClient):
    """여기엔 함수 커스텀이나 pass한 함수만 작성"""

    def __init__(self, default_model, api_keys):
        self.api_key = choice([key.strip() for key in api_keys.split(",")])
        print("OpenAI API KEY: ", self.api_key)

        super().__init__(
            default_model,
            OpenAI(api_key=self.api_key, timeout=600.0, max_retries=2),
            AsyncOpenAI(api_key=self.api_key, timeout=600.0, max_retries=2),
        )
