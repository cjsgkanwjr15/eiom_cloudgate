from enum import Enum
from src.utils import CustomException


class GPTFormErrorCode(Enum):
    UNKNOWN_ERROR = {
        "code": 2000,
        "message": "답변 생성 중 문제가 발생했습니다. 관리자에게 문의해주세요.",
    }
    TOOL_CALL_PENDING = {
        "code": 2001,
        "message": "작업 처리중입니다. 답변이 완료된 후 다시 질문해주세요.",
    }


class GPTFormException(CustomException):
    def __init__(self, error_code: GPTFormErrorCode):
        super().__init__(error_code)
