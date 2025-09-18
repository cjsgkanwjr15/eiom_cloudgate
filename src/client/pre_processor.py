from src.utils import ChatData
from src.client.ai_client import BaseAIClient
from src.client.db_client import MysqlClient
from src.client.talk_client import ChannelTalk


class PreProcessor:
    """DB 작동 가능한지 체크
    채팅데이터 전처리 및 DB 입력
    gpt메세지 포매팅"""

    def __init__(self, chat_data, ai_client, db_client, talk_client):
        self.chat_data: ChatData = chat_data
        self.ai_client: BaseAIClient = ai_client
        self.db_client: MysqlClient = db_client
        self.talk_client: ChannelTalk = talk_client

    def need_to_save(self):
        """저장할 필요 없는경우 반환"""
        need_save, reason = self.chat_data.need_to_save()
        if need_save:
            return True, "저장조건 만족"
        else:
            print(f"저장하지 않는 이유: {reason}")
            return False, reason

    def set_and_get_messages(self, hours=None, limit=None):
        if self.chat_data.files_exist():
            self.chat_data.set_files()

        rows = self.db_client.setting_transaction(hours, limit)
        preprocessed_rows = self.talk_client.preprocess_file(rows)

        messages = self.ai_client.form_gpt_messages(preprocessed_rows)
        print("최초 생성 messages:", messages)
        return messages

    def need_to_answer(self):
        """AI 답변이 필요 없는 경우를 반환"""
        need_answer, reason = self.chat_data.need_to_answer()
        if need_answer:
            return True, "답변조건 만족"
        else:
            print(f"답변하지 않는 이유: {reason}")
            return False, reason
