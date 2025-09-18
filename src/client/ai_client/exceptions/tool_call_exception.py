from enum import Enum
from src.utils import CustomException


class ToolCallErrorCode(Enum):
    UNKNOWN_ERROR = {"code": 4000, "message": "알 수 없는 오류가 발생했습니다."}
    INVALID_TOOL_CALL = {"code": 4001, "message": "실행 중 오류가 발생했습니다."}
    MISSING_ARGUMENTS = {"code": 4002, "message": "필수 인자가 누락되었습니다."}


class ToolCallException(CustomException):
    def __init__(self, error_code: ToolCallErrorCode, args=None):
        super().__init__(error_code)

    def print_error(self):
        print(f"ToolCallException: {self.error_name}", args)
