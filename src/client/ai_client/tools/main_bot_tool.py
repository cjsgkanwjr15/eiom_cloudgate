main_tools = [
    ### 예약 내역 조회
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_reservation_phone_number_info",
    #         "description": "",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "phone_number": {
    #                     "type": "string",
    #                     "description": "고객이 제공한 전화번호. 형태는 01012345678의 형태로, 공백이나 - 등을 반드시 모두 제외하고 가져와야 함 (필수). 만약 확인이 필요한 전화번호가 여러 개라면, 쉼표(,)로 구분하여 가져와야 함.",
    #                 },
    #             },
    #             "required": ["phone_number"],
    #         },
    #     },
    # },
    ### 특정 날짜 예약 가능한 시간대 조회
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_reservation_date_info",
    #         "description": "",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "want_to_check_date": {
    #                     "type": "string",
    #                     "description": "고객이 예약 원하는 날짜. 형태는 yyyy-mm-dd의 형태로 가져와야 함 (필수). 만약 확인 원하는 날짜가 여러 개라면, 쉼표(,)로 구분하여 가져와야 함.",
    #                 }
    #             },
    #             "required": ["want_to_check_date"],
    #         },
    #     },
    # },
    {
        "type": "function",
        "function": {
            "name": "get_order_info",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "주문번호. 전화번호(010-0000-0000) 형태를 주문번호로 착오하지 말 것.",
                    },
                },
                "required": [
                    "order_id",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_id",
            "description": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "buyer_cellphone": {
                        "type": "string",
                        "description": "주문자 분의 연락처(010-0000-0000). 고객님께서 제공한 형태와 관계없이 반드시 하이픈을 포함한 형태(010-0000-0000)로 작성할 것.",
                    },
                },
                "required": [
                    "buyer_cellphone",
                ],
                "additionalProperties": False,
            },
        },
    },
    {  ### cafe24 취소접수
        "type": "function",
        "function": {
            "name": "take_cancel_process",
            "description": "고객이 취소를 원하는 상품이 속한 주문번호, 상품 주문번호, 예금주, 계좌, 입금 은행을 가져오는 기능입니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "주문번호는 20250725-0002391와 같은 형식입니다. 고객이 202507250002391처럼 붙여서 제공하더라도 20250725-0002391로 분리하여야 합니다. 분리할 때는 '-'를 기준으로 앞은 주문일자이므로 이를 이용하여 분리하면 쉽습니다. ",
                    },
                    "reason_type": {
                        "type": "string",
                        "description": "고객이 취소를 요청한 이유를 그룹화하여 나타낸 것입니다. 아래 기준에 맞게 알맞은 영어 알파벳 값을 할당하세요. 원인이 고객의 변심인 경우: A를 할당, 원인이 상품불만족인 경우: E를 할당, 원인이 상품불량인 경우: K를 할당, 배송 오류인 경우: J를 할당, 그 외의 경우: I를 할당",
                    },
                    "customer_phone_number": {
                        "type": "string",
                        "description": "주문자 분의 연락처(010-0000-0000). 고객님께서 제공한 형태와 관계없이 반드시 하이픈을 포함한 형태(010-0000-0000)로 작성할 것.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "고객이 취소를 요청한 이유를 두 문장 내외로 깔끔하게 작성해주세요.",
                    },
                    "refund_bank_account_no": {
                        "type": "string",
                        "description": "고객이 환불을 받을 계좌번호를 작성해주세요. 고객이 -를 사용하여 끊어서 제공하더라도 하나로 합쳐서 작성해주세요.",
                    },
                    "refund_bank_account_holder": {
                        "type": "string",
                        "description": "고객이 환불을 받을 계좌의 예금주를 작성해주세요.",
                    },
                    "refund_bank_code": {
                        "type": "string",
                        "description": """고객이 환불받을 계좌의 은행코드 작성합니다. 고객이 말한 은행명을 그대로 작성하는 것이 아닌 고객이 말한 은행의 은행 코드를 작성해야합니다. 고객이 간혹 '국민, '새마을'과 같이 짧게 말하더라도 국민은행, 새마을금고라고 잘 매칭시켜야 합니다. 은행과 은행코드들을 정리한 딕셔너리는 다음과 같습니다. bank_code_dict = {
    "bank_02": "산업은행",
    "bank_03": "기업은행",
    "bank_04": "국민은행",
    "bank_07": "수협중앙회",
    "bank_11": "농협중앙회",
    "bank_12": "농협개인",
    "bank_13": "농협",
    "bank_20": "우리은행",
    "bank_23": "SC제일은행",
    "bank_26": "신한은행",
    "bank_292": "케이뱅크",
    "bank_293": "카카오뱅크",
    "bank_31": "iM뱅크(대구은행)",
    "bank_32": "부산은행",
    "bank_34": "광주은행",
    "bank_35": "제주은행",
    "bank_37": "전북은행",
    "bank_39": "경남은행",
    "bank_53": "씨티은행",
    "bank_71": "우체국",
    "bank_81": "하나은행",
    "bank_82": "농협회원조합",
    "bank_85": "새마을금고",
    "bank_295": "OK저축은행",
    "bank_296": "토스뱅크"
}""",
                    },
                },
                "required": [
                    "order_id",
                    "reason_type",
                    "reason",
                    "refund_bank_account_no",
                    "refund_bank_account_holder",
                    "refund_bank_code",
                    "customer_phone_number",
                ],
                "additionalProperties": False,
            },
        },
    },
    ### 예약 취소 요청
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "cancel_reservation_info",
    #         "description": "",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "name": {"type": "string", "description": "예약자 이름"},
    #                 "phone_number": {
    #                     "type": "string",
    #                     "description": "예약자 전화번호",
    #                 },
    #                 "schedule": {
    #                     "type": "string",
    #                     "description": "변경/취소 진행할 기존 예약 일정(날짜 및 시간). 'YYYY-MM-DD HH:MM' 형태로 반환",
    #                 },
    #             },
    #             "required": [
    #                 "name",
    #                 "phone_number",
    #                 "schedule",
    #             ],
    #             "additionalProperties": False,
    #         },
    #     },
    # },
]
