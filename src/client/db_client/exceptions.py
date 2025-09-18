from enum import Enum
from src.utils import CustomException


class DBErrorCode(Enum):
    UNKNOWN_ERROR = {
        "code": 4000,
        "message": "DB 조회중 문제가 발생했습니다. 관리자에게 문의해주세요.",
    }
    TOOL_RESULT_NOT_RECORDED = {"code": 4001, "message": ""}
    NEW_CHAT_DETECTED = {"code": 4002, "message": ""}


class DBException(CustomException):
    def __init__(self, error_code: DBErrorCode):
        super().__init__(error_code)
