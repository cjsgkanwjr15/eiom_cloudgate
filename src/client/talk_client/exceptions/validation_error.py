from enum import Enum
from src.utils import CustomException


class ChannelTalkErrorCode(Enum):
    UNKNOWN_ERROR = {"code": 1000, "message": "알 수 없는 오류가 발생했습니다."}
    VALIDATION_ERROR = {
        "code": 1001,
        "message": "처리중 오류가 발생했습니다. 다시 시도해주세요.",
    }


class ChannelTalkException(CustomException):
    def __init__(self, error_code: ChannelTalkErrorCode):
        super().__init__(error_code)
