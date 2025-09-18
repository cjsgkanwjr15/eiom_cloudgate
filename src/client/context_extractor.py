import itertools, re
from typing import Callable
from openai.types.chat import ChatCompletionSystemMessageParam

from .ai_client import BaseAIClient, prompts
from .chat_manager import ChatManager
from .db_client import MysqlClient

from ..utils import ChatData, QuestionDTO, print_function_args, print_function_result
import re
from ast import literal_eval
import math
from concurrent.futures import ThreadPoolExecutor


class ContextExtractor:

    def __init__(
        self,
        chat_data: ChatData,
        ai_client: BaseAIClient,
        db_client: MysqlClient,
        chat_manager: ChatManager,
    ):
        self.chat_data: ChatData = chat_data
        self.ai_client: BaseAIClient = ai_client
        self.db_client: MysqlClient = db_client
        self.chat_manager: ChatManager = chat_manager

    def get_context(self, messages: list, pre_messages_summary: dict = {}):
        """1. 발화문, 발화의도 추출
        2. 필요시 질문구분
        3. 관련 질의문 추출"""
        # 유저 발화 의도 파악, 관련 질문 추출해 시스템 프롬프트 생성
        user_conversations = self.form_user_conversations(
            messages, pre_messages_summary
        )
        # user_purpose = self.get_user_purpose(user_conversations)
        # self.db_client.write_user_purpose(user_purpose)

        # # 분류기 사용하면 이 코드 사용.
        # classifer_system_prompt = prompts.get_classifier_system_prompt(
        #     user_conversations
        # )
        # question_classification = self.get_ai_classification(classifer_system_prompt)
        # # 딕셔너리를 사용하여 main_prompt 변수를 매핑
        # case_list_mapping = {
        #     "1": prompts.case_list_1,
        #     "2": prompts.case_list_2,
        #     "3": prompts.case_list_3,
        #     "4": prompts.case_list_4,
        #     "5": prompts.case_list_5,
        # }
        # selected_case_list = case_list_mapping.get(question_classification)
        # qna_dtos = self.pick_related_questions(
        #     user_conversations, user_purpose, selected_case_list
        # )
        # related_qna_dtos = self.pick_related_questions(
        #     user_conversations, user_purpose, cases
        # )
        cases = prompts.case_list
        case_groups = self.split_question_sets(cases)

        results = []
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.extract_qna_dtos_CoT, user_conversations, group)
                for group in case_groups
            ]
            for future in futures:
                results.extend(future.result())

        # 최종 결과
        proper_qna_dtos = results
        return user_conversations, proper_qna_dtos

    def split_question_sets(self, data, min_group_size=15, max_group_size=23):
        n = len(data)
        print("n: ", n)
        # 데이터의 길이가 min_group_size보다 작으면 하나의 그룹으로 반환
        if n <= max_group_size:
            return [data]

        # 최소 그룹 수, 최대 그룹 수 계산
        min_groups = math.floor(n / max_group_size)
        max_groups = math.ceil(n / min_group_size)

        print("min, max: ", min_groups, max_groups)

        # 가장 적절한 그룹 수 선택 (최대한 균등하게)
        best_group_count = None
        best_diff = float("inf")

        for group_count in range(min_groups, max_groups + 1):
            group_size = n / group_count
            diff = abs(group_size - (min_group_size + max_group_size) / 2)
            if diff < best_diff:
                best_diff = diff
                best_group_count = group_count

        # 최종 그룹 크기 계산
        base_group_size = n // best_group_count
        remainder = n % best_group_count

        groups = []
        start = 0

        for i in range(best_group_count):
            # 앞쪽 그룹부터 하나씩 추가해서 remainder 수만큼 1개 더 가져감
            size = base_group_size + (1 if i < remainder else 0)
            groups.append(data[start : start + size])
            start += size

        return groups

    def extract_qna_dtos_CoT(self, user_conversations, cases: list[dict]):
        qna_dtos = [QuestionDTO(case) for case in cases]

        qna_dtos_CoT_system_prompt = self.create_qna_dtos_CoT_prompt(
            prompts.extract_manual_prompt,
            qna_dtos,
            user_conversations,
        )
        print({"qna_dtos_CoT_system_prompt": qna_dtos_CoT_system_prompt})

        final_qna_dto_CoT_extraction_content, _ = self.ai_client.get_ai_response(
            messages=[
                ChatCompletionSystemMessageParam(
                    role="system", content=qna_dtos_CoT_system_prompt
                ),
                ChatCompletionSystemMessageParam(
                    role="system", content=prompts.extract_manual_cot
                ),
            ],
            stream=False,
        )

        CoT_extracted_qna_dtos: list[QuestionDTO] = self.extract_qna_dtos_after_CoT(
            final_qna_dto_CoT_extraction_content, qna_dtos
        )

        print(
            "qna_dtos_after_CoT_extraction:",
            [vars(qna_dto) for qna_dto in CoT_extracted_qna_dtos],
        )

        return CoT_extracted_qna_dtos

    # def pick_related_questions(
    #     self, user_conversations, user_purpose, cases: list[dict]
    # ) -> list[QuestionDTO]:
    #     print("pick_related_questions executed")

    #     try:
    #         qna_dtos = [QuestionDTO(case) for case in cases]

    #         user_conversations = (
    #             user_conversations
    #             + "\n"
    #             + "마지막 대화에서의 고객의 의도: "
    #             + user_purpose
    #         )

    #         while len(qna_dtos) > 6:
    #             qna_dtos = self.compress_qna(
    #                 system_prompt=prompts.find_related_manual,
    #                 conversation=user_conversations,
    #                 qna_dtos=qna_dtos,
    #                 input=100,
    #                 output=6,
    #             )

    #         return qna_dtos
    #     except:
    #         raise

    def extract_qna_dtos_after_CoT(self, completion, qna_dtos_before_CoT):
        """
        주어진 텍스트에서 필요한 답변 (번호 리스트)만 추출합니다.
        이후 번호 리스트를 실제 배열로 만들어 반환합니다.
        """

        if "번호" not in completion:
            print("CoT 답변에 매뉴얼 번호 리스트가 없어 담당 매니저 연결")
            return "담당 매니저 통해 확인 후 답변드리겠습니다! 시간 소요될 수 있는 점 양해 부탁드립니다 :)"
        # 제거할 가능한 멘트들
        unwanted_phrases = [
            "필요한 매뉴얼의 번호",
        ]
        # 제거할 멘트들을 처리
        for phrase in unwanted_phrases:
            completion = completion.rsplit(phrase, 1)[-1]

        if "]" in completion:
            index = completion.find("]")
            completion = completion[: index + 1]

            # text 맨 앞, 맨 뒤의 특수 문자 모두 제거
            text = completion.strip()
            while text.startswith((".", ":", "-", "*", '"', " ", "\n")):
                text = text[1:]
                text = text.lstrip("\n")
            while text.endswith((":", "-", "*", '"', " ", "\n")):
                text = text[:-1]
            # 백틱 제거(쓸 일 없음)
            text = text.replace("`", "")
            completion = text.strip()
            completion = literal_eval(completion)

        else:
            completion = []

        # 유효한 인덱스만 사용해서 qna_dtos 추출
        qna_dtos_after_CoT = [
            qna_dtos_before_CoT[int(i) - 1]
            for i in completion
            if 0 <= int(i) - 1 < len(qna_dtos_before_CoT)
        ]

        return qna_dtos_after_CoT

    def extract_qna_dtos_after_CoT2(self, completion, qna_dtos_before_CoT):
        # 주어진 문자열

        # 정규 표현식을 사용해 숫자 또는 None 추출
        manual1_match = re.search(r"Response_manual1_number\)\s*(\w+)", completion)
        manual2_match = re.search(r"Response_manual2_number\)\s*(\w+)", completion)

        # 추출된 값을 리스트에 넣기
        manual1_number = manual1_match.group(1) if manual1_match else ""
        manual2_number = manual2_match.group(1) if manual2_match else ""

        # 숫자가 "None"이 아닌 경우에만 인덱스로 변환 (1부터 시작하므로 -1)
        indices = []
        if manual1_number.isdigit():
            indices.append(int(manual1_number) - 1)
        if manual2_number.isdigit():
            indices.append(int(manual2_number) - 1)

        # qna_dtos_before_CoT에서서 해당 인덱스에 맞는 원소 추출
        qna_dtos_after_CoT = [qna_dtos_before_CoT[i] for i in indices]

        return qna_dtos_after_CoT

    def create_qna_dtos_CoT_prompt(
        self,
        qna_dtos_CoT_prompt: str,
        qna_dtos: list[QuestionDTO],
        user_conversations: str,
    ) -> str:
        print("create_qna_dtos_CoT_prompt executed")
        manual_list = ""
        for index, qna_dto in enumerate(qna_dtos):
            manual_list += f"""{index+1}. [{index+1}번 매뉴얼]"""
            if qna_dto.manual_description:
                manual_list += f": {qna_dto.manual_description}"
            manual_list += "\n"

        if manual_list == "":
            return None

        else:
            qna_dtos_CoT_prompt_system_prompt = qna_dtos_CoT_prompt.format(
                user_conversations=user_conversations,
                manual_list=manual_list,
            )

        return qna_dtos_CoT_prompt_system_prompt

    def get_ai_classification(self, system_prompt):
        """ai 채팅을 바로 뱉게 만드는 함수"""
        print("get_ai_classification 실행")

        # main prompt 추가
        ai_classification_list = []
        ai_classification_list.insert(
            0, ChatCompletionSystemMessageParam(role="system", content=system_prompt)
        )
        max_tokens = 1
        keys = ["1", "2", "3", "4", "5"]

        # 답변 생성
        classification = self.ai_client.get_limitation_ai_response(
            ai_classification_list, max_tokens, keys
        )
        # main prompt 제거
        ai_classification_list.pop(0)

        return classification

    # @print_function_args()
    # @print_function_result(additional_info="유저 발화 의도")
    # def get_user_purpose(self, user_conversations) -> str:
    #     """유사한 프롬프트 찾기 전에 유저 질문의 의도 파악하기"""

    #     prompt = prompts.get_user_purpose_system_prompt(user_conversations)
    #     messages = [ChatCompletionSystemMessageParam(role="system", content=prompt)]
    #     user_purpose, _ = self.ai_client.get_ai_response(messages, stream=False)

    #     return user_purpose

    def pick_related_questions(
        self, user_conversations, user_purpose, cases: list[dict]
    ) -> list[QuestionDTO]:
        print("pick_related_questions executed")

        try:
            qna_dtos = [QuestionDTO(case) for case in cases]

            user_conversations = (
                user_conversations
                + "\n"
                + "마지막 대화에서의 고객의 의도: "
                + user_purpose
            )

            while len(qna_dtos) > 6:
                qna_dtos = self.compress_qna(
                    system_prompt=prompts.find_related_manual,
                    conversation=user_conversations,
                    qna_dtos=qna_dtos,
                    input=100,
                    output=6,
                )

            return qna_dtos
        except:
            raise

    def form_user_conversations(
        self,
        messages: list,
        pre_messages_summary: dict = {},
        pre_messages: dict = {},
    ) -> str:
        user_conversations = []

        if pre_message_summary := pre_messages_summary.get("summary"):
            user_conversations.append(
                f"""<버튼형 응대 내용 요약>
{pre_message_summary}"""
            )

        pre_message_form_input = [
            f"{key}: {value}"
            for input_dict in pre_messages_summary.get("form_input", [])
            for key, value in input_dict.items()
        ]
        if pre_message_form_input_str := "\n".join(pre_message_form_input):
            user_conversations.append(
                f"""<유저 폼 입력>
{pre_message_form_input_str}"""
            )

        conversation_list = []

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "user":
                if content:
                    if isinstance(content, str):
                        conversation_list.append(f"고객님: {content}\n\n")
                    else:
                        conversation_list.append("고객님: [사진 전송]\n\n")

            elif role == "assistant":
                if isinstance(content, str):
                    conversation_list.append(f"고객 응대 AI: {content}\n\n")

                tool_calls = []
                for tool_call in message.get("tool_calls", []):
                    function_name = tool_call["function"]["name"]
                    function_arguments = tool_call["function"]["arguments"]
                    tool_calls.append(
                        f"{function_name} 함수 호출, 인수: {function_arguments}"
                    )
                if tool_calls:
                    tool_calls_str = "\n".join(tool_calls)
                    conversation_list.append(f"고객 응대 AI: {tool_calls_str}\n")

            elif role == "tool":
                conversation_list.append(f"시스템: (함수 호출 결과: {content})\n\n")

        # Combine consecutive customer messages
        result = []
        customer_block = False

        for line in conversation_list:
            if line.startswith("고객님: "):
                if customer_block:
                    result[-1] += "\n" + line.replace("고객님: ", "", 1)
                else:
                    result.append(line)
                    customer_block = True
            else:
                result.append(line)
                customer_block = False

        if conversation := "\n".join(result):
            user_conversations.append(conversation)

        # 폼 입력 정보 가져오기
        form_info = [
            msg["content"]
            for msg in pre_messages
            if msg.get("content", "").startswith("[폼 입력]")
        ]

        # '[폼 입력]\n' 제거 및 연락처 변환
        processed_info = []
        for item in form_info:
            value = item.replace("[폼 입력]\n", "")
            if value.startswith("연락처: +82"):
                # +8210... -> 010... 변환
                value = value.replace("연락처: +82", "연락처: 0")
            processed_info.append(value)

        # 줄바꿈으로 연결
        result_str = "\n".join(processed_info)

        final_user_conversations = (
            result_str + "\n" + "\n".join(user_conversations) + "\n" + "\n"
        )

        return final_user_conversations

    def function_data(self, messages: list) -> str:
        function_data = []

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "assistant":

                tool_calls = []
                for tool_call in message.get("tool_calls", []):
                    function_name = tool_call["function"]["name"]
                    function_arguments = tool_call["function"]["arguments"]
                    tool_calls.append(
                        f"{function_name} 함수 호출, 인수: {function_arguments}"
                    )
                if tool_calls:
                    tool_calls_str = "\n".join(tool_calls)
                    function_data.append(f"{tool_calls_str}")

            elif role == "tool":
                function_data.append(f"함수 호출 결과: {content})\n\n")

        return "\n".join(function_data)

    def compress_qna(
        self,
        system_prompt: Callable[[str, str], str],
        conversation: str,
        qna_dtos: list[QuestionDTO],
        input: int,
        output: int,
    ) -> list[QuestionDTO]:
        """청크당 최대 input 개수는 AI토큰최대 제한인 300개로 맞춰야함. ','랑 예외 1개 있으니 298개로 제한"""
        qna_num = len(qna_dtos)
        chunk_num = int(qna_num / input) + 1  # 청크 개수
        split_num = int(qna_num / chunk_num) + 1  # 실제 청크당 질문 개수
        split_num = min(split_num, 298)

        chunked_qna_dtos = [
            qna_dtos[i : i + split_num] for i in range(0, len(qna_dtos), split_num)
        ]

        chunked_filtered_qna_dtos = [
            self._pick_answers(system_prompt, conversation, qna_dtos, output=output)
            for qna_dtos in chunked_qna_dtos
        ]

        return list(itertools.chain.from_iterable(chunked_filtered_qna_dtos))

    def _pick_answers(
        self,
        base_prompt: Callable[[str, str], str],
        conversation: str,
        qna_dtos: list[QuestionDTO],
        output: int,
    ) -> list[QuestionDTO]:
        """최대 input 개수는 AI토큰최대 제한인 300개로 맞춰야함. ','랑 예외 1개 있으니 298개로 제한"""
        token_num_max = 298
        max_num = len(qna_dtos)
        if max_num + 1 > token_num_max:
            raise ValueError(f"최대 {token_num_max}개의 질문만 가능합니다.")

        questions = "\n\n".join(
            f"{i}. {qna.user_purpose}" for i, qna in enumerate(qna_dtos, 1)
        )
        questions += f"\n\n{max_num + 1}. 해당하는 항목 없음"

        prompt = base_prompt(questions, conversation)
        messages = [ChatCompletionSystemMessageParam(role="system", content=prompt)]
        print({"pick prompt": messages})
        max_tokens = 2 * output - 1
        keys = [str(i) for i in range(1, max_num + 1)]
        keys.append(",")

        num_list_string = self.ai_client.get_limitation_ai_response(
            messages, max_tokens=max_tokens, keys=keys
        )
        print(num_list_string)
        num_list = list({int(num) for num in num_list_string.rstrip(",").split(",")})

        if max_num + 1 in num_list:
            return []

        return [qna_dtos[num - 1] for num in num_list if num <= max_num]
