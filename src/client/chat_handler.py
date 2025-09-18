import traceback, json
import types

from src.utils import ChatData, MetaData, QuestionDTO
from .ai_client import (
    BaseAIClient,
    GPTFormException,
    OpenAIException,
    ToolCallException,
    prompts,
    tools,
)
from .db_client import MysqlClient
from .talk_client import ChannelTalk
from .pre_processor import PreProcessor
from .context_extractor import ContextExtractor
from .chat_manager import ChatManager
from .tool_call_resolver import ToolCallResolver

from src.utils import time_info

from datetime import datetime, timedelta, timezone, date

from openai.types.chat import (
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)

UTC_PLUS_9 = timezone(timedelta(hours=9))
current_datetime = datetime.now(UTC_PLUS_9)
current_date_time = current_datetime.strftime("%Y-%m-%d %H:%M")
current_date = current_datetime.strftime("%Y-%m-%d")


class ChatHandler:
    """분류기, GPT설명추가 등 system prompt 만들고 질문 분류하는 작업 수행"""

    def __init__(
        self,
        chat_data: ChatData,
        ai_client: BaseAIClient,
        db_client: MysqlClient,
        talk_client: ChannelTalk,
        pre_processor: PreProcessor,
        context_extractor: ContextExtractor,
        chat_manager: ChatManager,
        tool_call_resolver: ToolCallResolver,
    ):
        self.chat_data: ChatData = chat_data
        self.ai_client: BaseAIClient = ai_client
        self.db_client: MysqlClient = db_client
        self.talk_client: ChannelTalk = talk_client

        self.pre_processor = pre_processor
        self.context_extractor = context_extractor
        self.chat_manager: ChatManager = chat_manager
        self.tool_call_resolver: ToolCallResolver = tool_call_resolver
        self.messages: list = None

        """AI에게 보내는 채팅 데이터"""

    async def run(self):
        response = None

        # pre_process
        # 실제 채팅 데이터 생성과 관련되지 않은 작업들
        try:
            need_save, status = self.pre_processor.need_to_save()
            if not need_save:
                print("return status: ", status)
                return status

            self.messages = self.pre_processor.set_and_get_messages()

            need_answer, assigned_status = self.pre_processor.need_to_answer()
            if not need_answer:
                print("return status: ", assigned_status)
                return assigned_status

            # 채팅 지연
            # sleep(10)
            # if self.db_client.detect_new_chat():
            #     print("return status: ", "새 채팅 발견")
            #     return "new chat detected"

            # 채널톡 유저 데이터 저장
            self.save_user_data_on_db()

            stop_ai_reponse_time = time_info.need_ai_works()
            print("stop_ai_reponse_time:", stop_ai_reponse_time)

            if not stop_ai_reponse_time:
                print("return status: ", "평일 10:00~17:00 사이에만 응대")
                return "평일 10:00~17:00 사이에만 응대"

            # 사전 대화 불러오기
            metadata: MetaData = self._get_metadata()
            self.pre_messages: list = json.loads(
                metadata.db_data.get("pre_messages", "[]")
            )
            self.pre_messages_summary: dict = json.loads(
                metadata.db_data.get("pre_messages_summary", "{}")
            )
        except Exception:
            self._handle_exception("프리셋에 오류가 발생했습니다.")
            return "preset error"

        # process
        try:
            system_prompt = None
            # 한번에 부를 수 있는 최대 tool 수, None이면 무제한
            tool_limit = None
            # 반복제한 횟수, 2면 toolcall 1번만 처리
            tool_call_limit = None
            repeat_limit = self._validate_repeat_limit(tool_call_limit)

            ####

            for i in range(repeat_limit):
                print("Try answer: ", i)
                user_conversations = self.context_extractor.form_user_conversations(
                    self.messages,
                    self.pre_messages_summary,
                    # self.pre_messages + self.messages
                )
                metadata: MetaData = self._get_metadata()
                print("metadata: ", metadata)

                ##########################################################################################################################################################
                user_conversations, qna_dtos_after_CoT = (
                    self.context_extractor.get_context(
                        self.messages,
                        self.pre_messages_summary,
                        # 요약 안시킬건데 버튼형응대 내용은 필요할 경우
                        # save_user_data_on_db에서 do_summary=False로 설정
                        # 이후 위에 두개를 쓰는게 아니라 아래 주석 내용 사용
                        # self.pre_messages + self.messages
                    )
                )
                qna_dtos_str_list = [qna.to_str() for qna in qna_dtos_after_CoT]
                self.db_client.write_qna_dtos(str(qna_dtos_str_list))
                ##########################################################################################################################################################

                # 시스템 프롬프트 생성
                system_prompt = self.create_system_prompt(
                    qna_dtos_after_CoT,
                    user_conversations,
                    metadata,
                )

                tool_choice = "none" if i >= repeat_limit - 1 else None
                # 챗 매니저로 답변 생성 및 전송
                ai_answer, tool_calls = self.chat_manager.get_ai_answer(
                    self.messages,
                    system_prompt,
                    stream=False,
                    tools=tools.main_tools,
                    tool_choice=tool_choice,
                    user_conversations=user_conversations,
                    chat_data_messages=self.messages,
                )

                if ai_answer is None and tool_calls is None:
                    break

                # 담당자 호출할 키워드, 담당자 아이디 입력
                # assign_ment_list: list = ["담당 매니저"]
                # assignee_list: list = ["383178"]  # 383178 고은비
                # self.chat_manager.call_assignee(
                #     ai_answer, assign_ment_list, assignee_list
                # )

                if tool_calls and self.tool_call_resolver.resolve(
                    self.messages,
                    tools.main_tools,
                    tool_calls,
                    metadata,
                    tool_limit=tool_limit,
                ):
                    conversation_id = self.db_client.add_tool_conversation()
                    self.chat_data.set_next_conversation(conversation_id)
                else:
                    break

            response = "Success"
        except (GPTFormException, OpenAIException, ToolCallException) as e:
            self._handle_exception(e.message)
            response = e.error_name
        except Exception:
            self._handle_exception(
                "죄송합니다. 오류가 발생했습니다. 관리자에게 문의해주세요."
            )
            response = "Total Unknown Error"

        return response or "None str"

    def _handle_exception(self, error_msg):
        self.db_client.revert_tool_call()
        print("Exception: ", error_msg)
        # self.chat_manager.send_message(error_msg)
        traceback.print_exc()

        # 에러나면 담당자 배정 코드
        # 호출할 담당자 아이디 입력
        # assignee_list: list = ["347522", "435419"]
        # self.chat_manager.assign_next_manager(assignee_list)

    def save_user_data_on_db(self):
        """유저 데이터 저장"""
        user_data = self.db_client.get_user_data()

        if user_data and user_data[0]:
            # 이미 pre_messages가 있으면 유저 기본정보를 저장했다는 뜻, pre_messages_summary는 확인 안해도 됨(아마)
            print("pre_messages already exist")
        else:
		        ################### 아래 부분 수정 ###################
		        # pre_messages, pre_messages_summary = self.get_pre_messages_info(
		        #     do_summary=False
		        # )
            pre_messages = []
            pre_messages_summary: dict = {"summary": "", "form_input": []}
            #######################################################
            self.db_client.write_user_data(
                "pre_messages", json.dumps(pre_messages, ensure_ascii=False)
            )
            self.db_client.write_user_data(
                "pre_messages_summary",
                json.dumps(pre_messages_summary, ensure_ascii=False),
            )

    def get_pre_messages_info(self, do_summary=False) -> dict:
        limit_overload = 10  # 과부하를 막기 위해 10번 이상 불러오지 못하게 함. 솔직히 1000개 이상 불러온건 문제가 있음;
        since = None
        checked_all_pre_messages = False
        pre_messages = []  # open 이벤트가 있기 전까지 정보를 전부 담아야함
        form_input = []
        for _ in range(limit_overload):
            user_chat_message_data = (
                self.talk_client.get_user_chat_messages(since=since, limit=100) or {}
            )
            since = user_chat_message_data.get("next")
            raw_messages = user_chat_message_data.get("messages", [])
            for message in raw_messages:
                if is_open := message.get("log", {}).get("action") == "open":
                    # open action이 되기 직전에는 항상 user의 최종 발화가 있다고 가정
                    if pre_messages:
                        print("pop:", pre_messages.pop())  # user 최종 발화 제거
                    checked_all_pre_messages = True

                    break

                plain_text = message.get("plainText")
                has_files = bool(message.get("files"))

                form_inputs = message.get("form", {}).get("inputs", [])

                text = ""
                if plain_text:
                    text += plain_text + "\n"
                if has_files:
                    text += "[파일 전송]" + "\n"

                person_type = message.get("personType")
                if person_type == "user":
                    pre_messages.append(
                        ChatCompletionUserMessageParam(role="user", content=text)
                    )
                elif person_type == "bot":
                    if form_inputs:
                        text += "[폼 전송]" + "\n"
                        valid_form_inputs: dict = {
                            input_data["label"]: input_data["value"]
                            for input_data in form_inputs
                            if input_data.get("label")
                            and input_data.get("value")
                            and input_data.get("dataType")
                            # in ["number", "string", "bool", "date", "button"]
                        }
                        form_input.append(valid_form_inputs)

                        text += "\n".join(
                            [
                                f"{label}: __________"
                                for label in valid_form_inputs.keys()
                            ]
                        )
                        pre_messages.append(
                            ChatCompletionAssistantMessageParam(
                                role="assistant", content=text.strip()
                            )
                        )
                        counter_text = "[폼 입력]\n" + "\n".join(
                            [
                                f"{label}: {value}"
                                for label, value in valid_form_inputs.items()
                            ]
                        )
                        pre_messages.append(
                            ChatCompletionAssistantMessageParam(
                                role="assistant", content=counter_text
                            )
                        )
                    else:
                        pre_messages.append(
                            ChatCompletionAssistantMessageParam(
                                role="assistant", content=text.strip()
                            )
                        )

            # asc에서 next가 안들어오면 더 없음
            if since is None:
                checked_all_pre_messages = True

            if checked_all_pre_messages:
                break

        pre_messages_summary: dict = {"summary": "", "form_input": []}
        if do_summary and pre_messages:
            summary = self.ai_client.get_ai_formed_data(
                prompts.get_pre_messages_summary(pre_messages)
            )
            pre_messages_summary = {"summary": summary, "form_input": form_input}

        return pre_messages, pre_messages_summary

    def _get_metadata(self) -> MetaData:
        """메타데이터 로딩"""
        metadata = MetaData()

        metadata.client_data = self.chat_data.get_user_data()

        user_data = self.db_client.get_user_data()
        metadata.db_data = (
            {"pre_messages": None, "pre_messages_summary": None}
            if user_data is None
            else {
                key: value
                for key, value in zip(
                    ["pre_messages", "pre_messages_summary"], user_data
                )
            }
        )

        for tool_call in self.db_client.get_user_tool_data():
            function_name, tool_name, args, return_value = tool_call

            # 이미 있으면 그냥 가져오고 없으면 새로 함수명 딕셔너리 생성
            metadata.tool_call_data[function_name] = metadata.tool_call_data.get(
                function_name, {}
            )
            metadata.tool_call_data[function_name][tool_name] = metadata.tool_call_data[
                function_name
            ].get(tool_name, [])
            metadata.tool_call_data[function_name][tool_name].append(
                {
                    "args": json.loads(args),
                    "return_value": json.loads(return_value),
                }
            )
        # metadata.tool_call_data = {
        #     "function":{
        #         "function_1_name": [{args:JSON, return_value:JSON},...],
        #         "function_2_name": [{args:JSON, return_value:JSON},...],
        #         ...
        #     }
        # }

        return metadata

    def _validate_repeat_limit(self, repeat_limit=10):
        """2회는 해둬야 toolcall이 한번이라도 돎. 10회 제한은 너무 많이 돌지 말라고 설정해둠"""
        repeat_limit = int(repeat_limit) if repeat_limit is not None else 10
        repeat_min, repeat_max = 2, 10
        return max(repeat_min, min(repeat_limit or repeat_max, repeat_max))

    def tool_call_apply(self, main_data, tool_call_data, func_name):
        for tool_call in tool_call_data.get(func_name, []):
            print(f"{func_name} tool_call: ", tool_call)
            args = tool_call["args"]
            return_value = tool_call["return_value"]
            if return_value and not isinstance(return_value, str):
                main_data[func_name] = return_value

    def create_system_prompt(
        self,
        qna_dtos: list[QuestionDTO],
        user_conversations: str,
        metadata,
    ) -> str:
        print("create_system_prompt executed")
        response_manuals = "\n\n".join(
            f"### 응대 매뉴얼 {i+1}\n"
            + qna_dto.manual_description
            + "\n"
            + qna_dto.response_manual
            for i, qna_dto in enumerate(qna_dtos)
        )

        response_manuals += """\n\n### 응대 매뉴얼 n
- 앞서 제공된 응대 매뉴얼만으로는 적절한 응대가 불가능할 경우, 어떠한 답변도 임의로 제공해서는 안 되며 반드시 실제 담당 매니저께 연결해 드려야 한다.
"""

        response_templates = """### 담당 매니저 연결 템플릿
- "고객님,

정확한 확인을 위해
담당 매니저와 연결해 드리겠습니다.

담당 매니저 연결은 시간이 다소 걸린다는 점
양해 부탁드립니다.

감사합니다."



### 톤앤매너 참고 템플릿(내용은 참고하지 말 것)
- "고객님,

제품 온라인 구매는 아래 링크를 통해 진행하실 수 있습니다.


🔗온라인 구매🔗
https://soltice.kr/product/list.html?cate_no=24


무통장입금의 경우 주문 시 결제 수단으로 선택하실 수 있습니다.

무통장입금은 주문 확정 후 진행되며
주문 확정 시 입금 안내 문자를 보내드리고 있는 점 안내드립니다. :)

감사합니다."



- "고객님,

솔티스 제품 외 타사 제품 관련 정보는
정확한 답변이 어려운 점 양해 부탁드립니다. 🥲

감사합니다."



- "고객님,

전화 문의를 희망하시는 경우
솔티스 고객센터(☎ 070-8657-1369)로 연락 부탁드립니다. :)

감사합니다.


🖇️솔티스 고객센터 영업 시간: 평일 10:00-17:00(점심 시간: 12:00-13:00)"



- "고객님,

배송 완료까지는 일반적으로 주문일부터
3-7일이 소요되는 점 안내드립니다. :)

감사합니다.


🖇️주문량 증가 시 출고가 1-2일 지연될 수 있습니다.

🖇️제주 및 도서·산간 지역의 경우 배송이 지연될 수 있으며, 추가 비용이 발생할 수 있습니다.

🖇️배송 일정은 택배사 사정에 따라 변동될 수 있습니다."



- "고객님,

해당 문의 내용은 ssgbio999@gmail.com로 메일 주시면
담당 부서에서 확인 도와드리겠습니다. :)

연락 주셔서 감사합니다."






### 응대 시작 시 반드시 사용해야 하는 첫인사 템플릿
- "안녕하세요, 고객님!

건강한 삶을 실현하기 위해 끊임없이 노력하는 건강기능식품 브랜드 솔티스입니다 :)"

### get_order_info 함수를 호출하는 멘트
- "주문번호 00000000-0000000로 get_order_info 함수를 호출한다."

### get_order_id 함수를 호출하는 멘트
- "연락처 010-0000-0000로 get_order_id 함수를 호출한다."

"""
        response_templates += "\n\n".join(
            f"### 응대 매뉴얼 {i+1} 답변 템플릿\n"
            + (getattr(qna_dto, "response_templates", "") or "")
            for i, qna_dto in enumerate(qna_dtos)
        )

        # 여기에 필요한 main_prompt에 필요한 데이터 추가

        # main_prompt의 DATA 영역에 변수명 똑같이 해서
        # {get_card_info} 이런식으로 추가 (이름 반드시 일치해야 함)

        # main_data = {
        #     "get_user_recent_CU_charge_info" : "",
        #     "get_card_order_list" : "",
        #     "get_card_info" : "",
        #     "get_card_refund_info" : "",
        #     "get_vacct_req_info" : "",
        #     "get_vacct_req_check" : "",
        #     "get_user_info" : "",
        #     "get_user_recent_CU_sent_info" : "",
        # }

        function_data = self.context_extractor.function_data(self.messages)

        main_data = {
            "get_order_info": "",
            "get_order_id": "",
            "current_date": f"{current_date}",
            "function_data": f"{function_data}",
        }

        tool_call_data = metadata.tool_call_data.get("function", {})
        for func_name in main_data.keys():
            self.tool_call_apply(main_data, tool_call_data, func_name)

        final_prompt = prompts.main_prompt.format(
            response_manuals=response_manuals,
            response_templates=response_templates,
            **main_data,
            user_conversations=user_conversations,
        )

        return final_prompt
