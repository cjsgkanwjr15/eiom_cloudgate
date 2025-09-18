import httpx
from openai import APIError

from .base_ai_client import BaseAIClient


class FailoverAIClient(BaseAIClient):
    """여기에 작성된 함수만 실행 가능"""

    def __init__(self, ai_clients: list[BaseAIClient] = []):
        self._ai_clients = ai_clients
        self._ai_client_index = 0

    def change_ai_client(self):
        self._ai_client_index = (self._ai_client_index + 1) % len(self._ai_clients)

    @property
    def ai_client(self):
        return self._ai_clients[self._ai_client_index]

    def get_ai_response(
        self,
        messages,
        stream=False,
        tools=None,
        model=None,
        temperature=0,
        tool_choice=None,
    ):
        err = None
        for _ in range(len(self._ai_clients)):
            try:
                return self.ai_client.get_ai_response(
                    messages,
                    stream,
                    tools,
                    model,
                    temperature,
                    tool_choice,
                )
            except (APIError, httpx.ReadTimeout) as e:
                print(e)
                err = e
                self.change_ai_client()

        raise err | Exception("All AI clients failed to response")

    def get_limitation_ai_response(self, messages, max_tokens, keys, model=None):
        err = None
        for _ in range(len(self._ai_clients)):
            try:
                return self.ai_client.get_limitation_ai_response(
                    messages, max_tokens, keys, model
                )
            except (APIError, httpx.ReadTimeout) as e:
                print(e)
                err = e
                self.change_ai_client()

        raise err | Exception("All AI clients failed to response")

    async def get_async_ai_response(
        self,
        messages,
        stream=False,
        tools=None,
        model=None,
        temperature=0,
        tool_choice=None,
    ):
        err = None
        for _ in range(len(self._ai_clients)):
            try:
                return await self.ai_client.get_async_ai_response(
                    messages,
                    stream,
                    tools,
                    model,
                    temperature,
                    tool_choice,
                )
            except (APIError, httpx.ReadTimeout) as e:
                print(e)
                err = e
                self.change_ai_client()

        raise err | Exception("All AI clients failed to response")

    async def get_async_limitation_ai_response(
        self, messages, max_tokens, keys, model=None
    ):
        err = None
        for _ in range(len(self._ai_clients)):
            try:
                return await self.ai_client.get_async_limitation_ai_response(
                    messages, max_tokens, keys, model
                )
            except (APIError, httpx.ReadTimeout) as e:
                print(e)
                err = e
                self.change_ai_client()

        raise err | Exception("All AI clients failed to response")
