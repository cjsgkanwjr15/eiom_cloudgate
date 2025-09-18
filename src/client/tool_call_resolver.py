import json

from src.utils import ChatData, MetaData

from .ai_client import ToolCallException, ToolCallErrorCode, BaseAIClient
from .db_client import MysqlClient
from .soltice_client import SolticeClient

from openai.types.chat import (
    ChatCompletionToolMessageParam,
    ChatCompletionAssistantMessageParam,
)


class ToolCallResolver:

    def __init__(
        self, chat_data: ChatData, ai_client: BaseAIClient, db_client: MysqlClient
    ):
        self.chat_data = chat_data
        self.ai_client = ai_client
        self.db_client = db_client

        self.messages = None

    def resolve(self, messages, tools, tool_calls, metadata: MetaData, tool_limit=None):
        self.messages = messages
        """tool_limit: 1회당 최대 tool_call 횟수/ None이면 무제한"""

        print("tool calls: ", json.dumps(tool_calls, ensure_ascii=False))
        if tool_limit:
            original_length = len(tool_calls)
            tool_calls = tool_calls[:tool_limit]
            if original_length != len(tool_calls):
                print("limited_tool_calls: ", tool_calls)

        # tool call 사용한다는 흔적 남기기
        write_on_conversations = self.write_tool_calls(tool_calls)
        if not write_on_conversations:
            return False

        function_infos = self.select_functions(tools) if tools else []

        tool_results = {}
        for tool_call in tool_calls:
            try:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])

                # 작업 가능한것만 작업
                tool_call_id = tool_call["id"]
                print("Process tool call:", tool_call_id)
                if function_info := function_infos.get(function_name):
                    self.check_leak(
                        function_args,
                        function_info.get("parameters", {}).get("required", []),
                    )
                    result = function_info["function"](self.messages, function_args)
                    print(f"Call {tool_call_id} result:", result)
                    tool_results[tool_call["id"]] = result
                else:
                    print(f"Invalid tool call: {tool_call_id}")
                    raise ToolCallException(ToolCallErrorCode.INVALID_TOOL_CALL)
            except ToolCallException:
                print(f"Tool call failed: {tool_call_id}")
                raise
            except Exception as e:
                print(f"Tool call failed: {tool_call_id}")
                raise ToolCallException(ToolCallErrorCode.UNKNOWN_ERROR) from e

        """기록가능하고 작동 성공한놈만 골라 작성"""
        did_tools, user_data_records, user_tool_data_records = [], [], []
        for tool_call in tool_calls:
            """작동한 놈들 기록"""
            tool_call_id = tool_call["id"]
            tool_result = tool_results.get(tool_call_id, None)

            did_tools.append(tool_call)
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            function_info = function_infos.get(function_name)
            """user_tool_data 기록할놈들"""
            target_list = (
                user_data_records
                if function_info["user_data"]
                else user_tool_data_records
            )
            target_list.append(
                {
                    "tool_name": function_name,
                    "args": function_args,
                    "return_value": tool_result,
                }
            )

        self.db_client.write_user_tool_data(user_tool_data_records)

        call_requests = self.write_tool_calls(did_tools)
        self.messages.append(call_requests)
        self.write_tool_results(tool_results)

        return bool(call_requests)

    def write_tool_calls(self, tool_calls):
        """tool_calls을 DB에 기록합니다."""
        print("write_tool_calls 실행")

        call_requests = ChatCompletionAssistantMessageParam(
            role="assistant", tool_calls=tool_calls
        )

        if not self.db_client.write_tool_calls(
            json.dumps(call_requests, ensure_ascii=False)
        ):
            return False

        return call_requests

    def write_tool_results(self, tool_results):
        """tool_results을 DB에 기록합니다."""
        print("write_tool_results 실행")

        tool_results = [
            ChatCompletionToolMessageParam(
                role="tool", tool_call_id=id, content=content
            )
            for id, content in tool_results.items()
        ]

        self.db_client.update_conversation_item(
            "tool_results", json.dumps(tool_results, ensure_ascii=False)
        )

        self.messages.extend(tool_results)

        return tool_results

    def pick_use_tools(self, prompt, tools):
        """프롬프트 내용에서 실제로 사용할 툴을 선택"""
        if not tools:
            return None

        tool_names = [tool["function"]["name"] for tool in tools]

        use_tool_names = [tool_name for tool_name in tool_names if tool_name in prompt]

        use_tools = [
            tool for tool in tools if tool["function"]["name"] in use_tool_names
        ]

        return use_tools or None

    def check_leak(self, function_args: dict, checklist: list):
        """필수요소중 부족한게 있는지 확인하는 함수"""
        # function_args의 key와 checklist의 요소들을 비교해 checklist에만 있는 요소들을 leaks에 담는다.

        leaks = set(checklist) - set(function_args.keys())
        if leaks:
            raise ToolCallException(ToolCallErrorCode.MISSING_ARGUMENTS, args=leaks)

    def select_functions(self, tools):
        """tools에서 function만 추출합니다."""
        return {
            name: self.functions[name]
            for tool in tools
            if tool.get("type") == "function"
            and (name := tool["function"]["name"]) in self.functions
        }

    @property
    def functions(self):
        return {
            "get_order_info": {
                "function": self.resolve_get_order_info,
                "user_data": False,
            },
            "get_order_id": {"function": self.resolve_get_order_id, "user_data": False},
            "take_cancel_process": {
                "function": self.resolve_cancel_order,
                "user_data": False,
            },
        }

    def resolve_get_order_info(self, messages, function_args):

        order_id = function_args.get("order_id", "")
        soltice_client = SolticeClient(self.db_client, self.ai_client)

        cafe24_info = soltice_client.get_order_info(order_id)

        return cafe24_info

    def resolve_get_order_id(self, messages, function_args):

        buyer_cellphone = function_args.get("buyer_cellphone", "")
        soltice_client = SolticeClient(self.db_client, self.ai_client)

        cafe24_info = soltice_client.get_order_id(buyer_cellphone)

        return cafe24_info

    def resolve_cancel_order(self, messages, function_args):
        soltice_client = SolticeClient(self.db_client, self.ai_client)
        print("cancel_order 실행")
        order_id = function_args.get("order_id", "주문번호 파악 불가")
        reason_type = function_args.get("reason_type", "취소 유형 파악 불가")
        reason = function_args.get("reason", "취소 사유 파악 불가")
        refund_bank_account_no = function_args.get(
            "refund_bank_account_no", "계좌번호 파악 불가"
        )
        refund_bank_account_holder = function_args.get(
            "refund_bank_account_holder", "예금주 파악 불가"
        )
        refund_bank_code = function_args.get("refund_bank_code", "은행 파악 불가")
        order = soltice_client.get_order_info(order_id)

        try:
            order_item = order[0] if isinstance(order, list) else order
            if "cash" in order_item["결제 수단"]:
                print("무통장입금 취소 절차")
                res_account = soltice_client.cancel_cash_order(
                    order_id,
                    reason_type,
                    reason,
                    refund_bank_code,
                    refund_bank_account_no,
                    refund_bank_account_holder,
                )
                if (
                    res_account
                    == "무통장입금 주문 취소 실패하였으므로 담당자 연결해야합니다."
                ):
                    print(res_account)
                    return res_account
            else:
                print("카드결제 취소 절차")
                res_card = soltice_client.cancel_card_order(
                    order_id, reason_type, reason
                )
                if res_card == "카드 주문취소에 실패했으므로 담당자를 연결해야합니다.":
                    print(res_card)
                    return res_card
            return "주문취소가 완료되었습니다."
        except Exception as e:
            print("주문 취소 과정 중 에러 발생")
            return "주문 취소 접수에 실패 했으므로 반드시 담당자 연결해야 합니다."

    # def resolve_request_new_reservation_info(self, messages, function_args):
    #     try:
    #         print("request_new_reservation_info")
    #         dermatology_client = DermatologyClient()

    #         # 필수 정보 추출
    #         phone_number = function_args.get("phone_number", "확인 필요")
    #         schedule = function_args.get("schedule", "확인 필요")

    #         # 필수 정보 체크
    #         if not all([phone_number, schedule]):
    #             return "모든 필수 정보를 입력해야 합니다."

    #         request_body = {
    #             "phone_number": phone_number,
    #             "schedule": schedule,
    #         }
    #         print(request_body)
    #         # DermatologyClient를 통해 예약 요청
    #         reservation_result = dermatology_client.request_new_reservation(
    #             request_body
    #         )
    #         print("reservation_result: ", reservation_result)
    #         return (
    #             f"{phone_number} {schedule} 예약 건 예약 접수 완료"
    #             if reservation_result is not None
    #             else f"{phone_number} {schedule} 예약 건 예약 접수 실패"
    #         )
    #     except Exception as e:
    #         print("Error in resolve_request_new_reservation_info:", str(e))
    #         return "tool call 에러로 인한 함수 호출 실패"

    # def resolve_request_call_reservation_info(self, messages, function_args):
    #     try:
    #         print("request_new_reservation_info")
    #         dermatology_client = DermatologyClient()

    #         # 필수 정보 추출
    #         phone_number = function_args.get("phone_number", "확인 필요")

    #         # 필수 정보 체크
    #         if not all([phone_number]):
    #             return "모든 필수 정보를 입력해야 합니다."

    #         request_body = {
    #             "phone_number": phone_number,
    #         }
    #         print(request_body)
    #         # DermatologyClient를 통해 예약 요청
    #         reservation_result = dermatology_client.request_call_reservation(
    #             request_body
    #         )
    #         print("reservation_result: ", reservation_result)
    #         return (
    #             f"{phone_number} 예약 건 예약 접수 완료"
    #             if reservation_result is not None
    #             else f"{phone_number} 예약 건 예약 접수 실패"
    #         )
    #     except Exception as e:
    #         print("Error in resolve_request_new_reservation_info:", str(e))
    #         return "tool call 에러로 인한 함수 호출 실패"
