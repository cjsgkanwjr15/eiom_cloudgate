import re

from src.utils import ChatData, print_function_args, deprecated
from .ai_client import BaseAIClient, prompts
from .db_client import MysqlClient
from .talk_client import ChannelTalk

from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionAssistantMessageParam,
)
from difflib import SequenceMatcher
from datetime import datetime, timedelta, timezone, date
from time import sleep

UTC_PLUS_9 = timezone(timedelta(hours=9))
current_datetime = datetime.now(UTC_PLUS_9)
current_date_time = current_datetime.strftime("%Y-%m-%d %H:%M")


class ChatManager:
    """chat_client와 db_client를 활용한 채팅 관리 클래스, tool_call 처리
    맨 하단 참고해 tool_call 함수 구현 요함"""

    def __init__(
        self,
        chat_data: ChatData,
        ai_client: BaseAIClient,
        db_client: MysqlClient,
        chat_client: ChannelTalk,
    ):
        self.chat_data: ChatData = chat_data
        self.ai_client = ai_client
        self.db_client = db_client
        self.chat_client = chat_client

    @print_function_args()
    def get_ai_answer(
        self,
        messages,
        system_prompt,
        stream=False,
        tools=None,
        tool_choice=None,
        user_conversations=None,
        chat_data_messages=[],
    ):
        """tool_choice: "none"일 경우 tool_call을 사용하지 않습니다."""
        print("final prompt generated")
        # 현재 system_prompt에 모든 대화내용을 넣는 구조이기 때문에 messages를 추가로 넣지 않음

        retries = 5
        for attempt in range(retries):
            ai_CoT_answer, tool_calls = self.get_CoT_ai_response(
                [],
                system_prompt,
                stream,
                tools,
                tool_choice,
            )
            print({"ai_CoT_answer": ai_CoT_answer})

            if tool_calls:
                return "", tool_calls

            ai_answer = self.extract_final_response(ai_CoT_answer)
            print("ai_answer_1: ", ai_answer)

            if ai_answer.startswith("(") and ai_answer.endswith(")"):
                if attempt < retries - 1:
                    continue  # 답변이 괄호로 감싸져 있는 경우 답변 다시 요청
                ai_answer = "정확한 확인을 위해 담당 매니저와 연결해 드리겠습니다. 담당 매니저 연결은 시간이 다소 걸린다는 점 양해 부탁드립니다."
            else:
                break

        #         # 이전 채팅에 인삿말 없었으면 채팅 맨 처음 부분에 인삿말 추가
        #         greeting_ment = """네 대표님! :)
        # """
        #         lines = user_conversations.split("\n")
        #         if not any("상담원: " in line and "네 대표님! :)" in line for line in lines):
        #             if not "네" in ai_answer and not self.contains_english(ai_answer):
        #                 ai_answer = f"{greeting_ment}\n\n{ai_answer}"

        # tool_call이 텍스트로 잡히면 해당 툴콜로 실행 시도

        matching_function_names = []
        # ai_answer에 multi_tool이나 parallel있으면 전체 답변 (ai_CoT_answer)에서 함수 이름 추출. 추출된 함수 없으면 담당 매니저 연결
        if "multi_tool" in ai_answer or "parallel" in ai_answer:
            if tools:
                for tool in tools:
                    function_name = tool["function"]["name"]
                    if function_name in ai_CoT_answer:
                        matching_function_names.append(function_name)
            if not matching_function_names:
                ai_answer = "담당 매니저 통해 확인 후 답변드리겠습니다! 시간 소요될 수 있는 점 양해 부탁드립니다."
        else:
            if tools:
                for tool in tools:
                    function_name = tool["function"]["name"]
                    if function_name in ai_answer:
                        matching_function_names.append(function_name)

        if matching_function_names:
            ai_answer = ""
            print("matching_function_names : ", matching_function_names)

            # tool_choice가 "none"이면 tool_call을 사용하면 안되는 단계므로 담당 매니저 연결
            if tool_choice != "none":
                final_tool_calls = self.get_tool_calls_from_ai_answer(
                    matching_function_names,
                    user_conversations,
                    messages,
                    tools,
                )

                if final_tool_calls:
                    return "", final_tool_calls
            ai_answer = "담당 매니저 연결드리겠습니다."

        emoji_pattern = (
            "["
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f700-\U0001f77f"  # alchemical symbols
            "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
            "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
            "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
            "\U0001fa00-\U0001fa6f"  # Chess Symbols
            "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027b0"  # Dingbats
            "]+"
        )
        text_emoticon_pattern = r"(\^\^|:\)|:-\)|:D|:P|;\)|ㅠㅠ|ㅜㅜ|^_^)"

        # 다., 요. 문장 줄바꿈
        ai_answer = re.sub(
            rf"\s*다[.!](?![\)\]\n]| {emoji_pattern}|{emoji_pattern}| {text_emoticon_pattern}|{text_emoticon_pattern})\s*",
            "다.\n\n",
            ai_answer,
        )
        ai_answer = re.sub(
            rf"\s*요[.!](?![\)\]\n]| {emoji_pattern}|{emoji_pattern}| {text_emoticon_pattern}|{text_emoticon_pattern})\s*",
            "요.\n\n",
            ai_answer,
        )
        ai_answer = re.sub(
            rf"\s*다[.!](?![\)\]\n])(\s?{emoji_pattern}|{text_emoticon_pattern})\s*",
            r"다.\1\n\n",
            ai_answer,
        )
        ai_answer = re.sub(
            rf"\s*요[.!](?![\)\]\n])(\s?{emoji_pattern}|{text_emoticon_pattern})\s*",
            r"요.\1\n\n",
            ai_answer,
        )

        # 숫자 기반 줄바꿈 처리
        ai_answer = re.sub(r"(?<![\[\(])(?<!\n)\s*(\d+\.\s)", r"\n\1", ai_answer)
        ai_answer = re.sub(r"(?<![\[\(])(?<!\n)\s*(\d+\)\s)", r"\n\1", ai_answer)

        # 마무리로 앞뒤 공백 정리
        ai_answer = re.sub(r"[ \t]+(?=\n)", "", ai_answer)  # 줄바꿈 앞 공백 제거
        ai_answer = re.sub(r"\n[ \t]+", "\n", ai_answer)  # 줄바꿈 뒤 공백 제거

        # 특정 문자들이 포함되어 있으면 ai_answer에서 이후 데이터 제거.
        phrases_to_check = [
            "더 궁금한 사항이 있으시면 언제든지 문의해 주세요.",
            "추가적인 문의 사항이 있으시면 언제든지 말씀해 주세요.",
            "추가 문의 사항이 있으시면 언제든지 말씀해 주세요.",
            "추가 문의사항이 있으시면 언제든지 말씀해 주세요.",
            "추가적인 문의사항이 있으시면 언제든지 말씀해 주세요.",
            "추가 문의사항이 있으시면 말씀해 주세요.",
            "추가적인 도움이 필요하시면 언제든지 말씀해 주세요.",
            "도움이 필요하시면 언제든지 문의해 주세요.",
            "더 궁금한 점 있으시면 언제든지 문의해주세요.",
            "궁금한 점 있으시면 언제든지 말씀해 주세요.",
            "추가적인 도움이 필요하시면",
            "추가적인 정보가 필요하시면 언제든지 말씀해 주세요.",
            "추가로 궁금한 점이 있으시면",
            "추가로 궁금한 사항이 있으시면",
            "추가로 궁금하신 점이 있으시면",
            "추가로 궁금하신 점이 있으면",
            "추가로 궁금하신 사항이 있으시면",
            "추가적으로 궁금하신 사항이 있으시면 언제든지 말씀해 주세요.",
            "추가적인 궁금한 점이 있으시면 언제든지 말씀해 주세요.",
            "추가로 도움이 필요하시면 언제든지 말씀해 주세요.",
            "더 궁금한 점이 있으시면 언제든지 문의해 주세요.",
            "다른 문의 사항이 있으시면 언제든지 말씀해 주세요.",
            "다른 문의사항이 있으시면 언제든지 말씀해 주세요.",
            "빠른 해결을 위해 최선을 다하겠습니다.",
            "추가로 필요한 사항이 있으시면 언제든지 말씀해 주세요.",
            "궁금하신 점도 언제든 편하게 문의해 주세요",
            "추가로 궁금하신 점 있으시면",
        ]

        # ai_answer를 엔터('\n') 기준으로 분리
        lines = ai_answer.split("\n")

        new_lines = []
        cut = False

        for line in lines:
            if cut:  # 이미 자르기로 결정된 경우는 무시
                continue
            for phrase in phrases_to_check:
                if phrase in line:
                    cut = True  # 이 문장 이후로는 건너뜀
                    break
            if not cut:
                new_lines.append(line)

        # 다시 '\n' 기준으로 합침
        ai_answer = "\n".join(new_lines).strip()

        # for phrase in phrases_to_check:
        #     index = ai_answer.find(phrase)
        #     if index != -1:
        #         ai_answer = ai_answer[:index].strip()
        #         break

        print("정규표현식 이후 ai_answer: ", ai_answer)

        is_same_answer = self.check_is_same_answer(
            ai_answer, chat_data_messages, check_is_same_answer_limit=3
        )

        if is_same_answer:
            changed_ai_answer_CoT = self.get_changed_ai_answer(
                user_conversations, ai_answer, chat_data_messages
            )
            print({"changed_ai_answer_CoT": changed_ai_answer_CoT})
            ai_answer = self.extract_final_response(changed_ai_answer_CoT)
            print({"changed_ai_answer": ai_answer})

        print({"final_ai_answer": ai_answer})

        # Welcome Message 세팅
        # AI 첫 답변인지 확인
        # assistant_exists = any(message["role"] == "assistant" for message in messages)
        # print("assistant_exists:", assistant_exists)

        # welcome_message = """안녕하세요."""
        # if not assistant_exists and "안녕" not in ai_answer:
        #     if self.db_client.detect_new_chat():
        #         print("new chat detected")
        #         return None, None
        #     self.send_message(welcome_message)
        # sleep(2)

        if self.db_client.detect_new_chat():
            print("new chat detected")
            return None, None

				################# 해당 부분 추가 #################
        # 담당자 배정 로직 실행
        assign_ment_list: list = [
            "담당 매니저",
        ]
        if any(word in ai_answer for word in assign_ment_list):
            self.chat_data.set_assigned()
            self.db_client.update_assignee("1")
        ###################################################

				######## 아래 send_message 파라미터에 self.chat_data.is_assigned 추가 ########
        self.send_message(ai_answer, self.chat_data.is_assigned) # 이 부분 수정
        messages.append(
            ChatCompletionAssistantMessageParam(role="assistant", content=ai_answer)
        )

        return ai_answer, None

    def check_is_same_answer(
        self, ai_answer, chat_data_messages, check_is_same_answer_limit=3
    ):
        print("check_is_same_answer 실행")
        print("chat_data_messages:", chat_data_messages)

        # 가장 최근 check_is_same_answer_limit개의 assistant 메시지를 가져오기
        latest_n_assistant_messages = [
            msg["content"]
            for msg in reversed(chat_data_messages)
            if msg["role"] == "assistant" and "content" in msg
        ][:check_is_same_answer_limit]

        # 이모지 제거 및 공백 제거 (이모지는 AI가 임의로 넣기 때문에 포함 관계 확인을 위하여)
        cleaned_ai_answer = self.remove_emoji(ai_answer).strip()

        for latest_assistant_message in latest_n_assistant_messages:
            print("latest_assistant_message 확인:", latest_assistant_message)

            latest_assistant_message_cleaned = self.remove_emoji(
                latest_assistant_message
            ).strip()

            if cleaned_ai_answer in latest_assistant_message_cleaned:
                print("새로운 답변이 이전 답변에 포함")
                return True

            similarity = SequenceMatcher(
                None, cleaned_ai_answer, latest_assistant_message_cleaned
            ).ratio()
            print("similarity:", similarity)

            if similarity > 0.90:
                print("유사도 90% 이상")
                return True

        print("동일 답변 아님")
        return False

    def remove_emoji(self, text):
        emoji_regex = self.emoji_regex

        return emoji_regex.sub("", text)

    def get_changed_ai_answer(self, user_conversations, ai_answer, chat_data_messages):
        print("get_changed_ai_answer 실행")

        latest_user_message = next(
            (
                msg
                for msg in reversed(chat_data_messages)
                if msg["role"] == "user" and "content" in msg
            ),
            None,
        )

        latest_question = self.remove_emoji(
            (latest_user_message["content"] if latest_user_message else "")
        ).strip()

        change_answer_prompt = [
            {
                "role": "system",
                "content": prompts.change_answer.format(
                    user_conversations=user_conversations,
                    ai_answer=ai_answer,
                    latest_question=latest_question,
                ),
            }
        ]
        # content, tool_calls = self.ai_client.get_ai_response(
        content = self.ai_client.get_ai_response(
            messages=change_answer_prompt, stream=False
        )

        return content

    def get_tool_calls_from_ai_answer(
        self,
        matching_function_names=None,
        user_conversations=None,
        messages=None,
        tools=None,
    ):
        print("함수 강제 호출 코드 실행")
        print("matching_function_names:", matching_function_names)
        function_list = ""
        for index, function_name in enumerate(matching_function_names):
            function_list += function_name
            if index != len(matching_function_names) - 1:
                function_list += "와 "
        prompt = f"""User_Conversation에서 고객의 마지막 말을 참고해서 {function_list}를 실행해줘.

[오늘 날짜 및 현재 시각]
현재 날짜 및 시간: {current_date_time}

[User's Conversations]
{user_conversations}"""
        _, final_tool_calls = self.ai_client.get_ai_response(
            messages=[ChatCompletionSystemMessageParam(role="system", content=prompt)],
            stream=False,
            tools=tools,
        )

        return final_tool_calls if final_tool_calls else None

    def get_CoT_ai_response(
        self,
        messages,
        system_prompt,
        stream,
        tools=None,
        tool_choice=None,
    ):

        #    messages.insert(
        #        1,
        #        ChatCompletionSystemMessageParam(
        #            role="system", content=prompts.main_CoT_prompt
        #        ),
        #    )
        messages.insert(
            0, ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        )

        content, tool_calls = self.ai_client.get_ai_response(
            messages=messages, stream=stream, tools=tools, tool_choice=tool_choice
        )

        messages.pop(0)

        return content, tool_calls

    def extract_final_response(self, text) -> str:
        """
        주어진 텍스트에서 step7 이후의 마지막 답변만 추출합니다.
        앞에 있는 특정 멘트들은 배열을 기반으로 제거합니다.
        양 끝에 있는 큰따옴표(")도 제거합니다. (앞 또는 뒤 하나만 있는 경우도 포함)
        """

        if "최종 답변" not in text:
            print(
                "CoT 답변에 최종 답변이 포함이 안 되어 있어서 담당 매니저 연결 멘트로 수정"
            )
            return "담당 매니저 연결드리겠습니다!"
        # step7 이후의 텍스트만 잘라내기
        # 제거할 가능한 멘트들
        unwanted_phrases = [
            "최종 답변은 다음과 같습니다:",
            "최종 답변:",
            "최종 답변",
        ]

        # 제거할 멘트들을 처리
        for phrase in unwanted_phrases:
            text = text.rsplit(phrase, 1)[-1]

        # text 맨 앞, 맨 뒤의 특수 문자 모두 제거
        text = text.strip()
        while text.startswith((".", ":", "-", "*", '"', " ", "\n")):
            text = text[1:]
            text = text.lstrip("\n")
        while text.endswith((":", "-", "*", '"', " ", "\n")):
            text = text[:-1]
        # 백틱 제거(쓸 일 없음)
        text = text.replace("`", "")

        # 최종 답변 반환
        return text.strip()

    def send_message(self, message, assign=False):
        """db저장과 전송까지 한번에 합니다."""
        if not message or message.isspace():
            return self.chat_data.get_answer()

        total_answer = self.chat_data.update_answer(message)
        self.db_client.update_conversation_item("answer", total_answer)
        self.chat_client.send_message(message, assign=assign)

        return total_answer

    @deprecated("send_by_paragraph 사용했을때 쓰던 것")
    def _should_send_message(self, chunk, paragraph):
        return (
            chunk.choices[0].finish_reason == "stop",
            (
                paragraph.endswith(self.end_patterns)
                and not re.search(r"\d\.$", paragraph)
            ),
            bool(self.emoji_regex.search(paragraph)),  # 이모지 패턴 검사
            (paragraph.endswith(", ") and len(paragraph) > 60),
        )

    end_patterns = (".", ".\n", "! ", "!\n", "? ", "?\n", "\n", "</link>")
    emoji_regex = re.compile(
        "["
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f700-\U0001f77f"  # alchemical symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027b0"  # Dingbats
        "]+"
    )

    def assign_manager_and_write(self, manager_id: str):
        try:
            self.chat_client.assign_manager_to_user_chat(manager_id)
            self.db_client.update_assignee(manager_id)
            print("상담사 배정 완료: ", manager_id)
            return True
        except Exception as e:
            print("상담사 배정 실패", e)
            return False

    def assign_next_manager(self, assignee_list: list[str]) -> bool:
        """담당자를 순차적으로 배정합니다."""
        for _ in range(len(assignee_list)):  # assignee_list 길이만큼만 반복
            assignee_num = self.db_client.get_assignee_number()
            print("assignee_num:", assignee_num)

            self.db_client.update_assignee_number(
                (assignee_num + 1) % len(assignee_list)
            )
            assignee = assignee_list[assignee_num]
            print("assignee:", assignee, "type(assignee):", type(assignee))

            # 상담사 배정 성공 시 루프 탈출
            if self.assign_manager_and_write(assignee):
                if self.chat_client.snooze_user_chat(self.chat_data.user_chat_id):
                    return True
                return True  # 성공하면 바로 종료
        return False

    def call_assignee(
        self, ai_answer: str, ments: list[str], assignee_list: list[str]
    ) -> bool:
        if any(ment in ai_answer for ment in ments):
            return self.assign_next_manager(assignee_list)

        return False

    # 영어 알파벳이 포함되어 있는지 확인하는 함수
    def contains_english(self, text):
        return bool(re.search(r"[a-zA-Z]", text))
