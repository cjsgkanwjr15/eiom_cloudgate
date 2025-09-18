import json, re, requests, base64
from time import sleep

from src.utils import ChatData
from .exceptions import ChannelTalkException, ChannelTalkErrorCode


class ChannelTalk:
    """채널톡 API 연결 클래스"""

    def __init__(
        self,
        chat_data: ChatData,
        x_access_key,
        x_access_secret,
        group_id=None,
        bot_name=None,
    ):
        self.chat_data: ChatData = chat_data
        if not x_access_key or not x_access_secret:
            raise ValueError("Access Key and Access Secret must be set")

        self.x_access_key = x_access_key
        self.x_access_secret = x_access_secret

        ################ 이 부분 수정 ################
        self.headers = {"Content-Type": "application/json", "accept": "*/*"}
        self.base_url = "https://www.thecloudgate.io:443/api/external/athome/ai"
        ######## 위 base_url 부분에서 athome으로 되어있는 부분 그대로 사용하면 됨 ########

        self.group_id = group_id
        self.bot_name = bot_name


    def check_is_closed_user_chat(self):
        try:
            api_url = f"https://api.channel.io/open/v5/user-chats/{self.chat_data.user_chat_id}"
            response = self._send_request_get_json("get", api_url)

            if not isinstance(response, dict):
                return False

            user_chat = response.get("userChat", {})
            if not isinstance(user_chat, dict):
                return False

            state = user_chat.get("state", "")
            if not isinstance(state, str):
                return False

            return state.lower() == "closed"

        except Exception as e:
            print(f"check_is_closed_user_chat 오류 발생: {e}")
            return False

    @staticmethod
    def replace_inequality_symbols_except_html_tag(text: str) -> str:
        """html tag를 제외한 부등호 기호를 치환합니다.
        일단 link 태그만 구현했습니다."""
        # 링크 태그 (<link ...>나 </link>)를 매칭하는 정규식 (대소문자 무시)
        link_pattern = re.compile(r"(<link\s*[^>]*?>|</link>)", re.IGNORECASE)
        # link_pattern을 기준으로 텍스트를 분할 (링크 태그는 결과 리스트에 포함됨)
        parts = link_pattern.split(text)

        # 분리된 각 부분에 대해 링크 태그가 아닌 경우 "<"와 ">"를 변환
        for i, part in enumerate(parts):
            if link_pattern.fullmatch(part):
                print("링크태그 감지,", part)
                # 링크 태그는 그대로 둠
                continue
            else:
                parts[i] = part.replace("<", "&lt;").replace(">", "&gt;")

        return "".join(parts)

    # send_message
    def send_message(self, message, assign=False):
        """채널에 메세지를 보냅니다"""
        if not message or message.isspace():
            return None

        api_url = f"{self.base_url}/message"

        if len(message) > 1000:
            message = self.split_long_string(message, max_length=1000)
            for msg in message:
                self._send_single_message(api_url, msg, assign)
        else:
            self._send_single_message(api_url, message, assign)

        return message
        
        
    # _send_single_message
    def _send_single_message(self, api_url, msg, assign=False):
        context = json.dumps(msg, ensure_ascii=False)
        print(f"send_message to {self.chat_data.user_chat_id}: {context}")
        data = {
            "brandId": int(self.chat_data.brand_id),
            "chatRoomId": int(self.chat_data.user_chat_id),
            "message": msg,
            "assignManager": assign,
        }

        try:
            response = self._send_request_get_json("post", api_url, json=data)
            print("send_message response: ", response)
        except requests.exceptions.RequestException as e:
            print(e)
        except Exception as e:
            print(e)

        sleep(0.2)
    
    

    def send_message_to_customer_support_group(self, type="담당자 호출 질문"):
        """channel_id, group_id 설정 필수!!! 채널에 메세지를 보냅니다"""
        channel_id = self.chat_data.channel_id
        user_chat_id = self.chat_data.user_chat_id
        group_id = self.group_id

        if channel_id is None or self.group_id is None:
            raise ValueError("Channel ID and Group ID must be set")
        print("send cs message")

        api_url = f"{self.base_url}/open/v5/groups/{self.group_id}/messages"

        # 보낼 내용 수정 필요
        data = {
            "blocks": [
                {
                    "type": "text",
                    "value": f'{type}: <link type="url" value="https://desk.channel.io/channels/{channel_id}/user_chats/{user_chat_id}">https://desk.channel.io/channels/{channel_id}/user_chats/{user_chat_id}</link>\n{self.chat_data.user_chat}',
                }
            ]
        }

        self._send_request_get_json("post", api_url, json=data)

    def change_user_profile(self, name=None, phone_number=None, user_id=None):
        print("change_user_profile 실행")

        # profile_data를 조건부로 생성
        profile_data = {
            k: v
            for k, v in {"name": name, "mobileNumber": phone_number}.items()
            if v is not None
        }

        if not profile_data:
            print("No profile data to update.")
            return

        api_url = f"{self.base_url}/open/v5/users/{user_id}"
        data = {"profile": profile_data}

        self._send_request_get_json("patch", api_url, json=data)

    def get_file_url(self, user_chat_id, file_key):
        api_url = f"{self.base_url}/open/v5/user-chats/{user_chat_id}/messages/file?key={file_key}"
        print("get_file_url:", api_url)

        return self._send_request_get_json("get", api_url)["result"]

    def get_manager_list(self, since=None, limit=None):
        """매니저 기본 25개까지 가져옵니다"""
        print("get manager list")
        api_url = f"{self.base_url}/open/v5/managers"
        params = {"since": since, "limit": limit}

        return self._send_request_get_json("get", api_url, params)

    def invite_manager_to_user_chat(self, manager_ids: list):
        """팔로워를 지정합니다."""
        print("invite manager to user chat: ", manager_ids)

        # 정상 작동시 해당 코드 제거
        # manager_ids_param = "&".join(
        #     f"managerIds={manager_id}" for manager_id in manager_ids
        # )
        # api_url = f"{self.base_url}/open/v5/user-chats/{self.chat_data.user_chat_id}/invite?botName={self.bot_name}&{manager_ids_param}"

        api_url = (
            f"{self.base_url}/open/v5/user-chats/{self.chat_data.user_chat_id}/invite"
        )
        params = {"botName": self.bot_name, "managerIds": manager_ids}

        self._send_request_get_json("patch", api_url, params=params)

    def assign_manager_to_user_chat(self, manager_id):
        """bot_name 설정 필수!!! 매니저를 지정합니다."""
        room_id = self.chat_data.user_chat_id
        url = f"https://api.channel.io/open/v5/user-chats/{room_id}/assign-to/managers/{manager_id}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "x-access-key": self.x_access_key,
            "x-access-secret": self.x_access_secret,
        }
        params = {"botName": "None"}

        response = requests.patch(url, headers=headers, params=params)
        print("response.json():", response.json())

        if response.json().get("type") == "notFoundError":
            raise ValueError("상담사 배정 실패: notFoundError 발생")

    def get_user_chat_messages(self, order="asc", limit=None, since=None):
        """유저 채팅 메세지를 가져옵니다. 기본적으로 오래된걸 먼저 가져옵니다. default 25개"""
        print("get_user_chat_messages 실행")

        api_url = (
            f"{self.base_url}/open/v5/user-chats/{self.chat_data.user_chat_id}/messages"
        )
        params = {"sortOrder": order, "since": since, "limit": limit}

        return self._send_request_get_json("get", api_url, params=params)

    def upload_file(self, file_name, file):
        """주의! 해당 채팅방에서만 해당 사진을 사용할 수 있음"""
        print("파일업로드")
        api_url = f"https://media.channel.io/cht/v1/pri-file/{self.chat_data.channel_id}/user-chats/{self.chat_data.user_chat_id}/message/{file_name}"
        files = file.read()

        # return file_info
        response = requests.post(api_url, data=files)
        return response.json()

    def post_file(self, message=None, file_infos: list = None, button=None):
        print("파일 메세지")
        api_url = (
            f"{self.base_url}/open/v5/user-chats/{self.chat_data.user_chat_id}/messages"
        )
        req_dict = {}
        if message:
            req_dict["blocks"] = [{"type": "text", "value": message}]
        if file_infos:
            # file infos 리스트여야 함.
            req_dict["files"] = file_infos
        response = requests.post(
            api_url,
            json=req_dict,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "x-access-key": self.x_access_key,
                "x-access-secret": self.x_access_secret,
            },
        )
        response.raise_for_status()
        print("파일 전송 response: ", response.json())

    def preprocess_file(self, messages: list[tuple]):
        """메세지의 파일 키를 전처리합니다."""
        print("preprocess_file 실행")
        preprocessed_messages = []

        for message in messages:
            # [사진 전송] 이라고 말한 것으로 대체 마스킹. 원하지 않을시 주석처리
            if message[7] == "files":
                message = list(message)
                message[3] = "[사진 전송]"
                message[7] = "text"
                message[8] = None
                message = tuple(message)

            # 아래는 정상 처리 로직
            if message[7] == "files":
                preprocessed_message = (
                    message[2],
                    json.dumps(
                        [
                            self.get_base64_file(
                                self.get_file_url(message[1], file_key)
                            )
                            for file_key in json.loads(message[3])
                        ]
                    ),
                    *message[4:],
                )
                preprocessed_messages.append(preprocessed_message)
            else:
                preprocessed_messages.append(message[2:])

        return preprocessed_messages

    def get_base64_file(self, file_url):
        print("get_base64_file of", file_url)
        file = self.get_file(file_url)
        return base64.b64encode(file).decode("utf-8")

    @staticmethod
    def get_file(file_url):
        print("get_file of", file_url)

        try:
            response = requests.get(url=file_url)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(e)

    @staticmethod
    def split_long_string(text, max_length=1000):
        # 문장부호를 기준으로 문자열을 분할
        text += "\n"
        sentences = re.split(r"([.!?\n])", text)
        result, current_chunk = [], ""

        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + sentences[i + 1]

            # 현재 문장 추가 후 길이 확인
            if len(current_chunk) + len(sentence) > max_length:
                result.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence

        # 마지막 남은 chunk 추가
        if current_chunk:
            result.append(current_chunk.strip())

        return result

    def _send_request_get_json(self, method, api_url, **kwargs):
        try:
            # `requests` 모듈의 메서드를 동적으로 선택
            request_method = getattr(requests, method.lower(), None)
            if request_method is None:
                raise ValueError("Invalid method")

            # 요청 보내기
            response = request_method(api_url, headers=self.headers, **kwargs)

            # 응답 상태 코드 확인
            response.raise_for_status()

            # JSON 응답 반환
            res = response.json()
            print("response: ", res)
            return res
        except requests.exceptions.RequestException as e:
            print(e)

    def snooze_user_chat(self, user_chat_id):
        """담당자 연결된 문의 보류중 처리"""

        url = f"https://api.channel.io/open/v5/user-chats/{user_chat_id}/snooze"

        headers = {
            "Content-Type": "application/json",
            "x-access-key": self.x_access_key,
            "x-access-secret": self.x_access_secret,
        }

        bot_name = "None"

        # if self.chat_data.channel_id == "195100":
        #     bot_name = "오아 테스트"

        params = {
            "duration": "P14D",
            "botName": bot_name,
        }  # duration은 필요에 맞게 수정

        try:
            response = requests.put(url, headers=headers, params=params)
            response.raise_for_status()  # 오류 발생 시 예외

            return True

        except Exception as e:
            # print(f"Error: {e}")  # 필요시 에러 메시지 출력
            return False
