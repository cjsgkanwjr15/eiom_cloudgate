import json, re
from datetime import datetime, timedelta


class ChatData:
    """
    현재 들어온 채팅과 답변에 관련한 데이터 클래스
    그냥 전체 공용 config class라고 생각해도 좋음
    ************************************************************
    user_id와 user_chat_id는 반드시 값을 넣을것!!
    DB 및 통계낼 때 unique 조건 검사하는데 null값이면 오류발생함
    ************************************************************
    """

    def __init__(self, body, is_live=True):
        self._is_live = is_live

        # .get()을 사용하여 키가 없는 경우 None을 반환하도록 합니다.
        self.refer = body.get("refers", {})
        self.refer_userchat = self.refer.get("userChat", {})
        self.refer_user = self.refer.get("user", {})
        self.user_profile = self.refer_user.get("profile", {})
        self.user_id: str = self.refer_userchat.get("userId")
        self.user_chat_id: str = self.refer_userchat.get("id")
        self.assignee_id = self.refer_userchat.get("assigneeId")
        self.team_id = self.refer_userchat.get("teamId")
        self.manager_ids = self.refer_userchat.get("managerIds", [])
        self.reply_count = self.refer_userchat.get("replyCount")
        self.tags: list[str] = self.refer_userchat.get("tags", [])
        self.user_name = self.user_profile.get("name")
        self.user_mobile_number = self.user_profile.get("mobileNumber")
        self.user_email = self.user_profile.get("email")

        self.entity = body.get("entity", {})
        self.meet = self.entity.get("meet")  # 통화연결이면 있음
        self.channel_id = self.entity.get("channelId")
        self.user_chat = self.entity.get("plainText")
        self.person_type = self.entity.get("personType")
        self.action = self.entity.get("log", {}).get("action")
        self.files = self.entity.get("files", [])
        self.workflow_button = self.entity.get("workflowButton")
        self.support_bot_id = self.entity.get("workflow", {}).get("id")

        # 유저의 채팅 시간 추출
        self.chat_time = self.extract_chat_time(self.entity.get("createdAt"))

        # handling_workflow_id가 None인 경우, source의 page 값에서 workflowId 추출
        self.support_bot_id = self.support_bot_id or self.extract_workflow_id(
            self.refer_userchat.get("source", {}).get("page")
        )

        # 커스텀 데이터
        # 데이터 전처리
        # question의 주체
        self.role = self.determine_role(self.person_type)

        self.conversation_id: str | None = None
        self.chat_type = "text"
        self.file_types = None
        self.file_keys = None

        # 한줄씩 출력한 채팅 데이터
        self.answers = []

    @property
    def is_live(self):
        # is_live가 False가 아니면 무조건 실제 배포 상황으로 간주합니다.
        return self._is_live is not False

    def extract_chat_time(self, created_at_timestamp):
        if created_at_timestamp is not None:
            return datetime.fromtimestamp(created_at_timestamp / 1000.0) + timedelta(
                hours=9
            )
        return None

    def extract_workflow_id(self, page_url):
        match = re.search(r"workflows/([^?]+)", page_url) if page_url else None
        return match.group(1) if match else None

    def determine_role(self, person_type):
        return person_type if person_type in ["user", "bot"] else "manager"

    def __str__(self):
        return f"ChatData(user_id={self.user_id}, user_chat_id={self.user_chat_id}, assignee_id={self.assignee_id}, reply_count={self.reply_count}, user_chat={self.user_chat}, person_type={self.person_type}, action={self.action}, files={self.files})"

    def __repr__(self):
        return str(self)

    def files_exist(self):
        return bool(self.files)

    def set_file_types(self):
        self.chat_type = "files"
        self.file_types = [
            (
                re.search(r"\.([^.]+)$", file["name"]).group(1)
                if re.search(r"\.([^.]+)$", file["name"])
                else "etc"
            )
            for file in self.files
        ]

    def set_file_keys(self):
        self.file_keys = [file.get("key") for file in self.files]

    def alter_chat(self, message):
        self.user_chat = message
        return self.user_chat

    def set_files(self):
        self.set_file_types()
        self.set_file_keys()
        self.alter_chat(json.dumps(self.file_keys, ensure_ascii=False))

    def get_user_data(self):
        """Metadata에 저장할 유저 정보를 반환합니다. 다른 용도로 사용 금지"""
        return {
            "name": self.user_name,
            "mobile_number": self.user_mobile_number,
            "email": self.user_email,
        }

    def is_bot_message_of(self, bot_ids: list):
        """해당하는 봇 메세지인지 여부를 반환"""
        return self.support_bot_id in bot_ids

    def is_action(self):
        """action인지 여부를 반환"""
        return self.action is not None

    def is_button(self):
        """버튼인지 여부를 반환"""
        return self.workflow_button is True

    def is_team_supported(self, team_ids: list):
        """특정 팀에 배정되어있는지 확인"""
        return self.team_id in team_ids

    def is_user_message(self):
        """사용자 메시지인지 여부를 반환"""
        return self.person_type == "user"

    def is_bot_message(self):
        """봇 메시지인지 여부를 반환"""
        return self.person_type == "bot"

    def is_assigned(self):
        """매니저에게 배정되어있는지 여부를 반환"""
        return self.assignee_id is not None

    def need_to_save(self):
        if self.is_action():
            return False, "action"

        if self.is_button():
            return False, "button"

        if self.is_bot_message():
            return False, "bot message"

        if self.meet is not None:
            return False, "meet"

        if self.is_live is False:
            # Appenv를 production으로 하지 않은 상황에서 원하는 로직 작성
            return True, "not live need save"
        else:
            # Appenv를 production으로 한 상황에서 원하는 로직 작성

            # 이런식으로 쓰면 됨. 커스텀 알아서 하면 됨
            if self.is_bot_message_of([]):
                return False, "answer-banned bot message"
            if self.is_team_supported([]):
                return False, "answer-banned team supported"
            if self.has_tags_in([]):
                return False, "answer-banned tags"

            return True, "live need to save"

    def has_tags_in(self, tags: list = []):
        """해당 태그들중 하나라도 가지고 있는지 여부"""
        return not set(self.tags).isdisjoint(set(tags))

    def need_to_answer(self):
        if not self.is_user_message():
            return False, "not user message"

        # assignee가 없을때만 답변
        if self.assignee_id is not None:
            # 특정 담당자를 제외한 담당자에게 배정될때만 답변금지
            if self.assignee_id not in []:
                return False, "assigned to manager"

        return True, "live need to answer"

    def is_first_message(self):
        return self.reply_count in {None, 0}

    def get_unique_key(self):
        return (self.user_id, self.user_chat_id)

    def set_conversation_id(self, conversation_id: str):
        self.conversation_id = conversation_id

    def update_answer(self, answer):
        """답변을 쌓아서 db에 저장해야할 때 사용합니다."""
        self.answers.append(answer)
        return self.get_answer()

    def get_answer(self):
        """답변을 반환합니다."""
        return "\n".join(self.answers)

    def set_next_conversation(self, next_conversation_id: str):
        self.set_conversation_id(next_conversation_id)
        self.answers.clear()

    def get_chat_info(self):
        return (
            self.user_chat,
            self.chat_type,
            (
                json.dumps(self.file_types)
                if self.chat_type == "files"
                else self.file_types
            ),
        )
