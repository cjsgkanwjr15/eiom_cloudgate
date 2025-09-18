from datetime import datetime, time, timedelta

from .static_data import holiday_list


class TimeInfo:
    """시간 관리 클래스"""

    def __init__(self):
        self.now = datetime.utcnow() + timedelta(hours=9)
        print("현재시간:", self.now)

        self.is_live = None

        self.weekdays = ["월", "화", "수", "목", "금", "토", "일"]

    def set_now(self, dt: datetime):
        print("현재시간 수정:", dt)
        self.now = dt

    @property
    def now_time(self):
        return self.now.time()

    def set_live(self, is_live=None):
        self.is_live = is_live

    @property
    def today_str(self):
        return self.now.strftime(
            f"%Y년 %m월 %d일 {self.weekdays[self.now.weekday()]}요일"
        )

    @property
    def today_date(self):
        return self.now.strftime("%Y-%m-%d")

    @property
    def is_holiday(self):
        return self.today_date in holiday_list.get(str(self.now.year), {}).keys()

    @property
    def is_weekend(self):
        return self.now.weekday() >= 5

    def need_ai_works(self):
        """AI 답변이 나가야할 시간인지 확인"""
        # AI 실제 작동 시간인지 반환합니다.
        # 필요시 pre_processor등 다른곳에서 사용하세요.
        # 답변 자체를 막는 등으로 사용할 수 있습니다.
        if self.is_live:
            return True
            # 특정 시간대에만 응대하도록 하고싶으면 이곳을 수정하세요.
            # if not self.is_holiday and not self.is_weekend:
            #     # ---------------------------------------------------------
            #     # 평일 10:00~17:00 사이에만 답변
            #     start = time(10, 00)
            #     end = time(17, 00)
            #     current_time = self.now.time()  # 일관성을 위해 self.now 사용
            #     if start <= current_time < end:
            #         print("현재 시각: ", current_time)
            #         print("평일 운영시간 내 응답")
            #         return True
            #     else:
            #         print("현재 시각: ", current_time)
            #         print("평일 운영시간 외 응답하지 않음")
            #         return False
            # ---------------------------------------------------------
        else:
            # 테스트 상황
            return True


# 해당 모듈은 다른데서 초기화시 인자로 넣지 말고, from src.utils import time_info처럼 사용하세요.
time_info = TimeInfo()
