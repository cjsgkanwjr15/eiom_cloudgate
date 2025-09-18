from enum import Enum
from src.utils import CustomException
from openai import APIError, RateLimitError


class OpenAIErrorCode(Enum):
    UNKNOWN_ERROR = {
        "code": 3000,
        "message": "답변 생성 중 문제가 발생했습니다. 관리자에게 문의해주세요.",
    }
    RATE_LIMIT_EXCEEDED = {
        "code": 3001,
        "message": "AI 답변이 지연되고있습니다. 잠시 후 다시 시도해주세요.",
    }


class OpenAIException(CustomException):
    def __init__(self, api_error: APIError):
        print("APIError:", api_error)
        # https://platform.openai.com/docs/guides/error-codes/python-library-error-types
        if isinstance(api_error, RateLimitError):
            error_code = OpenAIErrorCode.RATE_LIMIT_EXCEEDED
        else:
            error_code = OpenAIErrorCode.UNKNOWN_ERROR

        super().__init__(error_code)
