from openai import AzureOpenAI, AsyncAzureOpenAI
from random import choice

from .base_ai_client import BaseAIClient


class AzureAIClient(BaseAIClient):
    """여기엔 함수 커스텀이나 pass한 함수만 작성"""

    def __init__(
        self, default_model, api_keys, azure_endpoints, api_version="2024-08-01-preview"
    ):
        api_keys = [key.strip() for key in api_keys.split(",")]
        endpoints = [endpoint.strip() for endpoint in azure_endpoints.split(",")]
        self.endpoint, self.api_key = choice(list(zip(endpoints, api_keys)))

        print("endpoint:", self.endpoint, "openAI API KEY: ", self.api_key)

        super().__init__(
            default_model,
            AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=api_version,
                timeout=600.0,
                max_retries=2,
            ),
            AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=api_version,
                timeout=600.0,
                max_retries=2,
            ),
        )
