import types


class QuestionDTO:
    """qna를 이용하기 위한 dto"""

    def __init__(
        self,
        case: dict[
            "manual_description",
            "response_manual",
            "response_templates",
        ],
    ):
        """qna를 이용하기 위한 dto
        user_purpose: 사용자의 의도
        user_question_example: 사용자의 질문 예시(Deprecated)
        response_manual: 사용자의 의도에 대한 (답변|답변 방식)을 생성하는 (문장|함수)
        response_example: 사용자의 의도에 대한 (답변|답변 방식) 예시(자주 사용하지 않음)
        question_set_manual: question_set의 메뉴얼을 생성할 때만 조건 비교용으로 사용되는 문장
        """
        self.manual_description = case.get("manual_description")
        self.response_manual = case["response_manual"]
        self.response_templates = case.get("response_templates")

    # def get_case_purpose(self):
    #     return (
    #         f"{self.user_purpose}\n{self.question_set_manual}"
    #         if self.question_set_manual
    #         else self.user_purpose
    #     )

    def get_response_manual(self, metadata):
        if isinstance(self.response_manual, str):
            return self.response_manual
        elif isinstance(self.response_manual, types.FunctionType):
            return self.response_manual(metadata)
        else:
            raise ValueError("response_manual must be a string or a function")

    def to_str(self):
        string = f"manual_description: {self.manual_description}"

        return string

    def to_guideline(self, metadata):
        string = f"""{self.manual_description}
{self.get_response_manual(metadata)}"""
        return string
