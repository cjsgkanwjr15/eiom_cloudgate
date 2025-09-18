import json
import httpx
from openai import OpenAI, Stream, APIError, AsyncOpenAI, AsyncStream
from typing import Iterable
from tenacity import (
    retry,
    RetryCallState,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)
from openai.lib.azure import AzureOpenAI, AsyncAzureOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolChoiceOptionParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL

from .exceptions import GPTFormException, GPTFormErrorCode

from ...utils import print_function_args, print_function_result


def print_after_retry(retry_state: RetryCallState):
    if retry_state.outcome and retry_state.outcome.failed:
        print(f"예외 발생: {retry_state.outcome.exception()}")
        print(f"재시도 중... (시도 횟수: {retry_state.attempt_number}회)")


class BaseAIClient:
    """여기에 작성된 함수만 실행 가능"""

    def __init__(self, default_model, ai_client, async_ai_client):
        self.default_model = default_model
        self.ai_client: AzureOpenAI | OpenAI = ai_client
        self.async_ai_client: AsyncAzureOpenAI | AsyncOpenAI = async_ai_client

    @print_function_args()
    @retry(
        retry=retry_if_exception_type((APIError, httpx.ReadTimeout)),
        wait=wait_random_exponential(min=600, max=1200),
        stop=stop_after_attempt(6),
        after=print_after_retry,
    )
    @print_function_result()
    def get_ai_response(
        self,
        messages: Iterable[ChatCompletionMessageParam],
        stream: bool | None = False,
        tools: list | None = None,
        model: str | None = None,
        temperature: float | None = 0,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ) -> tuple[str | None, list[dict] | None]:
        model = model or self.default_model

        completion: ChatCompletion | Stream[ChatCompletionChunk] = (
            self.ai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                tools=tools,
                stream=stream,
                tool_choice=tool_choice,
            )
        )

        if isinstance(completion, ChatCompletion):
            content = completion.choices[0].message.content
            tool_calls = completion.choices[0].message.tool_calls

            # dict형태로 반환시킴
            tool_calls_dict = (
                [tool_call.model_dump() for tool_call in tool_calls]
                if tool_calls
                else None
            )

            return content, tool_calls_dict
        elif isinstance(completion, Stream):
            chunks: list[ChatCompletionChunk] = [chunk for chunk in completion]
            content, tool_calls = self.collect_content_and_tool_calls(chunks)

            return content, tool_calls
        else:
            raise ValueError(
                f"Unknown completion type: {type(completion)}. Expected ChatCompletion or Stream[ChatCompletionChunk]."
            )

    @print_function_args()
    def collect_content_and_tool_calls(self, chunks: list[ChatCompletionChunk]):
        avaliable_deltas = [chunk.choices[0].delta for chunk in chunks if chunk.choices]

        collected_contents = [delta.content for delta in avaliable_deltas]
        collected_tool_callses = [delta.tool_calls for delta in avaliable_deltas]

        content = self.collect_content(collected_contents)
        tool_calls = self.collect_tool_calls(collected_tool_callses)

        return content, tool_calls

    def collect_content(self, collected_contents: list):
        """실제로 컨텐츠가 None이 아니라 들어온거면 합쳐서 반환, 아니면 None 반환"""

        real_collected_contents = [
            content for content in collected_contents if content is not None
        ]

        return "".join(real_collected_contents) if real_collected_contents else None

    def collect_tool_calls(self, collected_tool_callses: list):
        """실제로 ToolCall이 들어온거면 합쳐서 반환, 아니면 None 반환"""
        flattened_list = []
        for sublist in collected_tool_callses:
            if sublist is None:
                continue
            for item in sublist:
                if item is None:
                    continue

                flattened_list.append(item)

        tool_calls: list[dict] = []
        for tool_calls_chunk in flattened_list:
            if tool_calls_chunk is None:
                continue

            if len(tool_calls) <= tool_calls_chunk.index:
                tool_calls.extend(
                    dict(id="", type="", function=dict(name="", arguments=""))
                    for _ in range(tool_calls_chunk.index - len(tool_calls) + 1)
                )
            tool_call: dict = tool_calls[tool_calls_chunk.index]

            if tool_calls_chunk.id:
                tool_call["id"] += tool_calls_chunk.id
            if tool_calls_chunk.type:
                tool_call["type"] += tool_calls_chunk.type
            if tool_calls_chunk.function:
                if tool_calls_chunk.function.name:
                    tool_call["function"]["name"] += tool_calls_chunk.function.name
                if tool_calls_chunk.function.arguments:
                    tool_call["function"][
                        "arguments"
                    ] += tool_calls_chunk.function.arguments

        return tool_calls or None

    @print_function_args()
    @print_function_result()
    def get_ai_formed_data(self, prompt, user_inquiry=None, stream=False):
        messages = [ChatCompletionSystemMessageParam(role="system", content=prompt)]
        if user_inquiry is not None:
            messages.append(
                ChatCompletionUserMessageParam(role="user", content=user_inquiry)
            )

        content, _ = self.get_ai_response(
            messages,
            stream=stream,
            #   tool_choice="none"
        )

        return content

    @print_function_args()
    @retry(
        retry=retry_if_exception_type((APIError, httpx.ReadTimeout)),
        wait=wait_random_exponential(min=600, max=1200),
        stop=stop_after_attempt(6),
        before=print_after_retry,
    )
    @print_function_result()
    def get_limitation_ai_response(self, messages, max_tokens, keys, model=None):
        model = model or self.default_model
        logit_bias = {self.token_ids[key]: 100 for key in keys}

        completion = self.ai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=max_tokens,
            logit_bias=logit_bias,
        )

        return completion.choices[0].message.content

    @print_function_args()
    @retry(
        retry=retry_if_exception_type((APIError, httpx.ReadTimeout)),
        wait=wait_random_exponential(min=600, max=1200),
        stop=stop_after_attempt(6),
        before=print_after_retry,
    )
    @print_function_result()
    async def get_async_ai_response(
        self,
        messages: Iterable[ChatCompletionMessageParam],
        stream: bool | None = False,
        tools: list | None = None,
        model: str | None = None,
        temperature: float | None = 0,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
    ):
        model = model or self.default_model

        completion: ChatCompletion | AsyncStream[ChatCompletionChunk] = (
            await self.async_ai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                tools=tools,
                stream=stream,
                tool_choice=tool_choice,
            )
        )

        if isinstance(completion, ChatCompletion):
            content = completion.choices[0].message.content
            tool_calls = completion.choices[0].message.tool_calls

            return content, tool_calls
        elif isinstance(completion, AsyncStream):
            chunks: list[ChatCompletionChunk] = [chunk async for chunk in completion]
            content, tool_calls = self.collect_content_and_tool_calls(chunks)

            return content, tool_calls
        else:
            raise ValueError(
                f"Unknown completion type: {type(completion)}. Expected ChatCompletion or Stream[ChatCompletionChunk]."
            )

    @print_function_args()
    @retry(
        retry=retry_if_exception_type((APIError, httpx.ReadTimeout)),
        wait=wait_random_exponential(min=600, max=1200),
        stop=stop_after_attempt(6),
        before=print_after_retry,
    )
    @print_function_result()
    async def get_async_limitation_ai_response(
        self, messages, max_tokens, keys, model=None
    ):
        model = model or self.default_model
        logit_bias = {self.token_ids[key]: 100 for key in keys}

        completion = await self.async_ai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=max_tokens,
            logit_bias=logit_bias,
        )

        return completion.choices[0].message.content

    def form_gpt_messages(self, preprocessed_rows):
        if not preprocessed_rows:
            return []

        gpt_messages = []

        for preprocessed_row in preprocessed_rows:
            (
                role,
                question,
                answer,
                tool_calls,
                tool_results,
                chat_type,
                file_types,
                _,
            ) = preprocessed_row

            if self.is_exist(question):
                if role == "manager":
                    gpt_messages.append(
                        ChatCompletionAssistantMessageParam(
                            role="assistant", content=question
                        )
                    )
                else:
                    if chat_type == "files":
                        questions = json.loads(question)
                        file_types = json.loads(file_types)

                        contents = [
                            (
                                ChatCompletionContentPartImageParam(
                                    type="image_url",
                                    image_url=ImageURL(
                                        url=f"data:image/{file_type};base64,{link}"
                                    ),
                                )
                                if file_type in ["png", "jpeg", "jpg", "webp", "gif"]
                                else ChatCompletionContentPartTextParam(
                                    type="text", text="(처리 불가한 파일 업로드)"
                                )
                            )
                            for link, file_type in zip(questions, file_types)
                        ]

                        gpt_messages.append(
                            ChatCompletionUserMessageParam(
                                role="user", content=contents
                            )
                        )
                    else:
                        gpt_messages.append(
                            ChatCompletionUserMessageParam(
                                role="user", content=question
                            )
                        )

            if self.is_exist(answer):
                gpt_messages.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant", content=answer
                    )
                )

            if self.is_exist(tool_calls):
                if self.is_exist(tool_results):
                    gpt_messages.append(json.loads(tool_calls))
                    gpt_messages.extend(json.loads(tool_results))
                else:
                    raise GPTFormException(GPTFormErrorCode.TOOL_CALL_PENDING)

        return gpt_messages

    @staticmethod
    def is_exist(log):
        """None, "" 값과 "-" 값은 없는 것으로 무시"""
        return log and log != "-"

    token_ids = {
        "case": "9994",
        "yes": "6763",
        "no": "1750",
        ",": "11",
        "0": "15",
        "1": "16",
        "2": "17",
        "3": "18",
        "4": "19",
        "5": "20",
        "6": "21",
        "7": "22",
        "8": "23",
        "9": "24",
        "10": "702",
        "11": "994",
        "12": "899",
        "13": "1311",
        "14": "1265",
        "15": "1055",
        "16": "1125",
        "17": "1422",
        "18": "1157",
        "19": "858",
        "20": "455",
        "21": "2040",
        "22": "1709",
        "23": "1860",
        "24": "1494",
        "25": "1161",
        "26": "2109",
        "27": "2092",
        "28": "2029",
        "29": "2270",
        "30": "1130",
        "31": "2911",
        "32": "1398",
        "33": "2546",
        "34": "3020",
        "35": "2467",
        "36": "2636",
        "37": "2991",
        "38": "3150",
        "39": "3255",
        "40": "1723",
        "41": "4987",
        "42": "4689",
        "43": "5320",
        "44": "3336",
        "45": "2548",
        "46": "4217",
        "47": "4146",
        "48": "3519",
        "49": "3796",
        "50": "1434",
        "51": "6231",
        "52": "6283",
        "53": "6798",
        "54": "6733",
        "55": "3152",
        "56": "5007",
        "57": "5085",
        "58": "4635",
        "59": "4621",
        "60": "1910",
        "61": "8954",
        "62": "8947",
        "63": "8876",
        "64": "2220",
        "65": "3898",
        "66": "3618",
        "67": "5462",
        "68": "4625",
        "69": "5759",
        "70": "2789",
        "71": "10018",
        "72": "8540",
        "73": "9912",
        "74": "9876",
        "75": "3384",
        "76": "7947",
        "77": "3732",
        "78": "4388",
        "79": "7767",
        "80": "2241",
        "81": "9989",
        "82": "10116",
        "83": "10127",
        "84": "9928",
        "85": "8017",
        "86": "7189",
        "87": "6818",
        "88": "2843",
        "89": "7479",
        "90": "2744",
        "91": "8956",
        "92": "10088",
        "93": "10573",
        "94": "10545",
        "95": "4129",
        "96": "6768",
        "97": "5170",
        "98": "5080",
        "99": "2058",
        "100": "1353",
        "101": "7959",
        "102": "7672",
        "103": "11914",
        "104": "12204",
        "105": "11442",
        "106": "13365",
        "107": "13665",
        "108": "11003",
        "109": "13923",
        "110": "7920",
        "111": "8780",
        "112": "12307",
        "113": "14075",
        "114": "13486",
        "115": "11999",
        "116": "14799",
        "117": "15607",
        "118": "14642",
        "119": "15970",
        "120": "6106",
        "121": "14503",
        "122": "14785",
        "123": "7633",
        "124": "16059",
        "125": "10676",
        "126": "16576",
        "127": "12807",
        "128": "8076",
        "129": "16891",
        "130": "9300",
        "131": "16412",
        "132": "16972",
        "133": "16518",
        "134": "17419",
        "135": "14953",
        "136": "17537",
        "137": "18663",
        "138": "17469",
        "139": "16840",
        "140": "10165",
        "141": "16926",
        "142": "18330",
        "143": "18445",
        "144": "15363",
        "145": "16620",
        "146": "19302",
        "147": "18902",
        "148": "19149",
        "149": "18235",
        "150": "5215",
        "151": "17395",
        "152": "17336",
        "153": "17773",
        "154": "19145",
        "155": "17385",
        "156": "18369",
        "157": "19676",
        "158": "19548",
        "159": "19218",
        "160": "9444",
        "161": "18881",
        "162": "18694",
        "163": "17666",
        "164": "18395",
        "165": "16461",
        "166": "19341",
        "167": "20469",
        "168": "13567",
        "169": "20335",
        "170": "12536",
        "171": "19603",
        "172": "19249",
        "173": "20898",
        "174": "20750",
        "175": "16080",
        "176": "19313",
        "177": "19227",
        "178": "18132",
        "179": "18438",
        "180": "7521",
        "181": "16813",
        "182": "17399",
        "183": "17104",
        "184": "15980",
        "185": "14741",
        "186": "14502",
        "187": "14780",
        "188": "13096",
        "189": "13589",
        "190": "9659",
        "191": "10037",
        "192": "8145",
        "193": "9244",
        "194": "8034",
        "195": "7866",
        "196": "6514",
        "197": "5695",
        "198": "4745",
        "199": "3204",
        "200": "1179",
        "201": "667",
        "202": "1323",
        "203": "14754",
        "204": "14397",
        "205": "17953",
        "206": "20007",
        "207": "21283",
        "208": "20021",
        "209": "23078",
        "210": "14028",
        "211": "20350",
        "212": "19584",
        "213": "20293",
        "214": "21401",
        "215": "21625",
        "216": "22705",
        "217": "24904",
        "218": "24437",
        "219": "25050",
        "220": "12806",
        "221": "22687",
        "222": "16427",
        "223": "22538",
        "224": "19427",
        "225": "18566",
        "226": "24960",
        "227": "26161",
        "228": "25017",
        "229": "25242",
        "230": "15752",
        "231": "22806",
        "232": "22280",
        "233": "22328",
        "234": "20771",
        "235": "22265",
        "236": "26277",
        "237": "26741",
        "238": "25706",
        "239": "26975",
        "240": "13312",
        "241": "24865",
        "242": "24472",
        "243": "25150",
        "244": "25291",
        "245": "23481",
        "246": "23488",
        "247": "25397",
        "248": "26247",
        "249": "26392",
        "250": "6911",
        "251": "24995",
        "252": "22581",
        "253": "26340",
        "254": "23388",
        "255": "6143",
        "256": "5780",
        "257": "28219",
        "258": "28320",
        "259": "28608",
        "260": "18542",
        "261": "28399",
        "262": "26378",
        "263": "28557",
        "264": "23685",
        "265": "25799",
        "266": "29054",
        "267": "30854",
        "268": "29994",
        "269": "30713",
        "270": "17820",
        "271": "29898",
        "272": "29086",
        "273": "28710",
        "274": "30998",
        "275": "25046",
        "276": "30895",
        "277": "30351",
        "278": "30873",
        "279": "31468",
        "280": "17713",
        "281": "28637",
        "282": "29459",
        "283": "30365",
        "284": "31250",
        "285": "28677",
        "286": "31652",
        "287": "32630",
        "288": "26678",
        "289": "31868",
        "290": "24130",
        "291": "31517",
        "292": "30907",
        "293": "31394",
        "294": "32078",
        "295": "29868",
        "296": "31788",
        "297": "31943",
        "298": "31367",
        "299": "25431",
        "300": "4095",
        "301": "22083",
    }
