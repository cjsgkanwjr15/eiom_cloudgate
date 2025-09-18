import asyncio, json, os, traceback

from src.client import *
from src.utils import time_info, ChatData

# APP_ENV 값에 따라 live, test 환경을 구분합니다.
# 해당 담당자 배정, 태그 허용 / 팀 허용 등 여부를 테스트시 주석처리하는 위험 없이 chat_data.is_live로 체크해 진행되도록 합니다.

is_live = os.getenv("APP_ENV") == "production"

# README.md를 따른 후, 최초 action 반영을 위해 이 주석줄을 지우고 initial commit을 날려주세요!

# 채널톡 설정
group_id = None if is_live else None
bot_name = None if is_live else None
# 채널톡 API KEY 설정
X_ACCESS_KEY = os.getenv("X_ACCESS_KEY")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

# DB 설정
"DB 기본 대화 데이터 조회 기간 설정"
hours: int = 24  # 시간제한
limit: int = None  # 개수제한
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# AI API KEY 및 모델 설정
# OpenAI 모델 및 키
CHAT_MODEL = os.getenv("CHAT_MODEL")
OPENAI_API_KEYS = os.getenv("OPENAI_API_KEYS")
# Azure 모델, 키 및 엔드포인트
AZURE_CHAT_MODEL = os.getenv("AZURE_CHAT_MODEL")
AZURE_OPENAI_API_KEYS = os.getenv("AZURE_OPENAI_API_KEYS")
AZURE_OPENAI_ENDPOINTS = os.getenv("AZURE_OPENAI_ENDPOINTS")


# from dotenv import load_dotenv

# load_dotenv()


def lambda_handler(event, context):
    """모든 기초 세팅만을 여기서 마치고 chat_handler.run()을 실행합니다.
    기본적으로 이 안에서는 비즈니스 로직(담당자 배정, 멘트 추가 등)을 하지 않습니다. 순수히 객체 초기화 용도로만사용합니다."""
    try:
        body = json.loads(event["body"])
        print(body)
        chat_data = ChatData(body, is_live=is_live)

        # Live서버 아니면 하루종일 켜져있도록 설정됨
        if now := chat_data.chat_time:
            time_info.set_now(now)

        time_info.set_live(is_live)

        # AI 클라이언트 변경하고싶으면 이부분 주석 변경

        ai_client = FailoverAIClient(
            ai_clients=[
                AzureAIClient(
                    AZURE_CHAT_MODEL, AZURE_OPENAI_API_KEYS, AZURE_OPENAI_ENDPOINTS
                ),
                OpenaiAIClient(CHAT_MODEL, OPENAI_API_KEYS),
            ]
        )
        # ai_client = AzureAIClient(
        #     AZURE_CHAT_MODEL, AZURE_OPENAI_API_KEYS, AZURE_OPENAI_ENDPOINTS
        # )
        # ai_client = OpenaiAIClient(CHAT_MODEL, OPENAI_API_KEYS)

        mysql_client = MysqlClient(chat_data, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
        mysql_client.set_default_limit(hours=hours, limit=limit)

        talk_client = ChannelTalk(
            chat_data, X_ACCESS_KEY, X_ACCESS_SECRET, group_id, bot_name
        )

        pre_processor = PreProcessor(chat_data, ai_client, mysql_client, talk_client)
        chat_manager = ChatManager(chat_data, ai_client, mysql_client, talk_client)
        context_extractor = ContextExtractor(
            chat_data, ai_client, mysql_client, chat_manager
        )
        tool_call_resolver = ToolCallResolver(chat_data, ai_client, mysql_client)

        chat_handler = ChatHandler(
            chat_data,
            ai_client,
            mysql_client,
            talk_client,
            pre_processor,
            context_extractor,
            chat_manager,
            tool_call_resolver,
        )

    except Exception:
        traceback.print_exc()
        return {"statusCode": 200, "body": "preset error"}

    response = asyncio.run(chat_handler.run())
    print(dict(response=response))

    return {"statusCode": 200, "body": response}
