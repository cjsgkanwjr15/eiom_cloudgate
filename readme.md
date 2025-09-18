# Lambda-Template-Purpose

해당 템플릿으로 새 프로젝트를 진행할 때 셋팅에 대한 가이드입니다.

# 사전준비

1. 채널톡 develop 계정 접근 권한 획득

- 채널톡 develop 계정 달라고 요청하십시오.

2. AWS 계정 생성

- AWS 계정 생성을 요청합니다. AWS 계정 관리자에게 email을 알려주셔야 합니다.
- AWS 계정 관리자가 IAM 사용자를 생성하고 MFA 등록 요청을 할 것입니다. 이때 Google Authenticator 등을 이용해 MFA를 등록합니다.
- AWS 계정 관리자가 이메일로 AWS 계정 정보를 보내줄 것입니다. 해당 정보를 받아서 저장합니다.
- 로그인 링크로 로그인 후, 비밀번호를 원하는 것으로 재설정합니다.

3. Github Organization 초대

- Github 계정 생성 후, 관리자에게 Github Organization 초대를 요청합니다.
- 초대를 수락하면 해당 Organization의 리포지토리에 접근할 수 있습니다.

4. OpenAI 접근 및 키 생성 권한 획득

- OpenAI 계정을 생성하고, Organization 초대를 요청합니다. (Owner 권한이어야 키 생성이 가능합니다.)
- OpenAI 계정 관리자가 이메일로 초대를 보내줄 것입니다. 해당 초대를 수락합니다.

5. Azure OpenAI 접근 및 키 생성 권한 획득

- 배경설명: 애저는 지역/프로젝트/배포유형/모델명 을 지정해야합니다.
  - 프로젝트명은 일반적으로 `generativelab-지역명-credit`으로 지정되어 있습니다.
  - 배포유형은 `Global Standard`로 해야합니다. 다른 유형(Fine-tuned, Batch 등)으로 하면 문제 발생할 수 있습니다.


- [애저 모델 버전별 가용량 확인 페이지](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models?tabs=python-secure#model-summary-table-and-region-availability) 에서 모델 버전별 가용 지역을 확인합니다.
- [애저 할당량 확인 페이지](https://oai.azure.com/resource/quota?wsid=/subscriptions/b24aa590-18ee-4da0-93f7-400a5a015ee3/resourceGroups/generativelab/providers/Microsoft.CognitiveServices/accounts/generativelab-australiaeast-credit&tid=80f1b1cf-c89d-48d7-8032-ae74be054cc8) 에서 할당량이 비어있는 지역에 챗모델을 배포해야 합니다. 해당 과정을 설명합니다.
  - Azure 로그인 정보는 관리자에게 요청합니다.
  - 해당 페이지에서 Global Standard / 원하는 모델명(보통은 gpt-4o)에 표시되어있는 지역별 TPM(Tokens Per Minute) 할당량을 확인하고, 비어있는 곳을 확인합니다.
    - 단, icb와 관련된 배포가 없는 지역을 선택해야 합니다. icb와 관련된 배포가 있는 지역은 사용할 수 없습니다.(ex: gpt-4o-2024-05-13-icb_payment_ai_agent_secure 등)
  - 우상단의 프로젝트명을 눌러 우측에 `Azure OpenAI Service resource` 탭을 띄웁니다.
  - `Azure OpenAI Service resource`를 비어있는것으로 확인된 지역 프로젝트를 선택합니다.
  - 해당 창에서 엔드포인트가 AZURE_OPENAI_ENDPOINTS, 키1가 AZURE_OPENAI_API_KEYS로 사용됩니다. 복사해두세요.
  - 하단의 `전환`을 눌러 해당 프로젝트로 이동합니다.
  - `+ 모델 배포`를 클릭하고, `기본 모델 배포`를 선택합니다.
  - gpt-4o 등 원하는 모델을 선택하고, `확인`을 누릅니다. 모델 배포 창이 띄워집니다.
  - `배포 세부 정보` 의 우측 `사용자 지정`을 클릭합니다. **배포 이름, 배포 유형을 열심히 선택해도 모델 버전을 변경하면 해당 내용이 초기화되니 과정을 지켜주세요**
  - 모델 버전을 원하는 버전으로 선택하고, 분당 토큰 속도 제한을 150K로 설정합니다.
  - 콘텐츠필터를 `CustomContentFilter`가 포함된 것으로 설정합니다. 기본 필터는 폭력, 성적 언어 등의 필터링 기준이 강해 답변이 나가지 않을 수 있습니다.
  - 배포 이름을 `{모델명}-{모델버전}_{프로젝트명}`으로 설정합니다.
    - 해당 배포이름이 AZURE_CHAT_MODEL로 사용됩니다. 복사해두세요.
    - ex) gpt-4o 모델의 2024-08-06 버전을 seoltab_teacher 프로젝트에 사용할 예정일 경우 `gpt-4o-2024-08-06_seoltab_teacher`로 설정합니다.
  - 배포 유형을 `글로벌 표준(Global Standard)`로 설정합니다. 해당 항목이 없으면 할당량이 남은 다른 지역부터 다시 선택해야 합니다.
  - `배포`를 누르면 배포 준비가 완료됩니다.

# 프로젝트 세팅 가이드

## 채널톡 채널 생성

**테스트 채널만 필요하면 테스트 채널만 파고, 고객사 채널도 필요하면 고객사 채널도 파세요.**

### 채널톡 기본 생성

- 채널톡 페이지 왼쪽 제일 아래 채널 아이콘(채널 목록)을 누릅니다.

![채널 목록](https://github.com/user-attachments/assets/f7ebbbc6-64a9-49f8-b906-647308cfecbf) ![채널 설정](https://github.com/user-attachments/assets/7f09b867-5296-4ce3-b105-a5b3e07da7df)

1. 기존 테스트 채널을 이용하는 경우

- 채널 리스트가 팝업으로 뜨면, 아래로 스크롤해 `z테스트 채널~`라고 되어있는 채널을 클릭합니다.
  - 해당 채널들은 이전에 테스트로 쓰였다가, tmp로 남아있는 채널입니다. 있으면 앞번호부터 써주세요
- 채널 설정을 클릭합니다. `일반 설정 > 채널 프로필` 을 클릭합니다.
- 채널명 부분을 서비스 이름 + `테스트` 로 쓰고, `저장` 버튼을 누릅니다.
- `성공적으로 업데이트되었습니다` 라고 왼쪽 하단에 뜨면 성공적으로 채널 이름이 변경됩니다.

2. 테스트 채널을 새로 만들어야하는 경우

- 채널 리스트가 팝업으로 뜨면, 제일 아래까지 스크롤 해서 `새 채널 만들기`를 클릭합니다.
- 서비스명은 해당하는 서비스 이름 + `테스트` 로 설정합니다. 홈페이지는 빈 채로 두고 `다음 단계로`를 클릭합니다.
- 업종은 `기타`로 선택합니다. 직원수는 10명 미만으로 설정하고 `새 채널 만들기`를 클릭합니다.
- 채널이 생성됩니다.

3. 배포 채널을 만들어야하는 경우

- 테스트 채널과 동일하게 하되, 서비스 이름 뒤에 `테스트`만 떼면 됩니다.
- 업종 설정이 불안하면 물어보세요~ 보통 테스트채널처럼 하긴 합니다.

**후속조치**

- 채널 설정의 `상담 > 팔로업 알림` 을 클릭합니다.
- `이메일` 등 항목들을 전부 끈 뒤, `저장`을 클릭합니다.
  - 맨처음에 유저가 채팅을 치면 개인정보 수집 동의 메세지가 가는건데, 안뜨는게 편합니다. 기본적으론 생성할때 끈다 라고 모두 인지하고 있다고 생각해주세요.
  - 기존 테스트 채널을 이용할 때에는 해당 설정이 이미 되어있을 수 있습니다.
  - 해당 과정을 진행하면 이후 테스트 진행시 맨 처음에 팔로업 알림이 생성되지 않습니다.

### 채널톡 API 설정

API와 웹훅 사용을 위해서는 결제 카드 등록 후, 플랜을 선택해야합니다.

1. 결제카드 등록

- 채널 설정을 클릭합니다. `구독 및 결제 > 결제 정보` 를 클릭합니다. 결제 카드 정보를 확인할 수 있습니다.
- 고객사 채널
  - **_우리 회사 카드 등록은 테스트 서버에서만 합니다. 실제 서비스 결제는 고객사가 직접 등록하도록 합니다._**
- 테스트 채널
  - 카드 등록 되어있으면 넘어가도 좋습니다.
  - 카드가 등록된게 없다면 아래 지침을 따릅니다.
    - 카드번호/유효기간/비밀번호앞2자리/사업자등록번호10자리 를 요청합니다.
    - `카드` 창에서 오른쪽의 `결제 수단 추가` 버튼을 클릭합니다.
    - 해당 카드 정보를 입력하고, `등록` 버튼을 클릭해 카드를 해당 채널에 등록합니다.

2. 플랜 설정
   **_고객사 채널에서 플랜 설정을 하면 결제가 시작됩니다!! 배포 테스트를 시작한게 아니라면, 결제하지 말고 냅두세요._**

- 채널 설정을 클릭합니다. `구독 및 결제 > 서비스 구독` 을 클릭합니다.
- `구독 개요`창에서 `플랜 업그레이드 ->` 버튼을 클릭합니다.
- 월(연 -25%가 아닙니다!) 을 클릭합니다.
- `얼리스테이지`를 선택합니다.

![구독 설정](https://github.com/user-attachments/assets/8fcdce9c-dafd-4df2-9b00-a9bdb6ffcb3a)

- 오른쪽 하단의 `플랜 변경`을 클릭합니다. 팝업창에서 `플랜 변경`을 다시 한번 클릭합니다.
- 기본 제공량 어쩌구저쩌구,,,월한도설정,,,선불충전... 팝업창이 뜨면 `다음에 하기`를 클릭합니다.
  - 해당 창은 안뜰수도 있습니다.
- 플랜 설정이 완료되었습니다.

![구독 확인](https://github.com/user-attachments/assets/30beb3f0-af1d-4e0b-89a8-a03e649e4274)

3. API 키 발급

- 채널 설정을 클릭합니다. `보안 및 개발 > API` 를 클릭합니다.
- 오른쪽 상단의 `새 인증 키 만들기`를 클릭합니다.
- 인증 키 이름은 ai_agent로 하고, `확인`을 클릭합니다.
- 인증 키 정보가 팝업으로 뜹니다. Access Key와 Access Secret을 메모장 등에 복사해둡니다.
  - `Access Secret`은 닫히면 다시 볼 수 없으니, 유의합니다.
    - 실수로 Secret을 확인하지 않고 창을 닫았다면, `수정` 로고를 눌러 삭제 후 재발급 받으면 됩니다.
- 인증 키 발급이 완료되었습니다.

![엑세스키 발급 완료 화면](https://github.com/user-attachments/assets/1b358e55-7049-4f0b-b95e-e85293fb529f)

## DB 생성

- mysql을 실행할 수 있는 환경에서 원하는 DB서버에 접속합니다. DB 서버 정보는 아래 링크에서 확인합니다.

[DB 정보](https://www.notion.so/801dd3ecee1d4fe3982d0058fd3ef744?pvs=4#c2e68808cc0c4b4d90ceb929fa300c77)

- **DB는 2개 파야합니다. 하나는 실제 배포시 사용되는 DB, 다른 하나는 테스트용 DB입니다.**
- 테스트용 DB의 이름은 실제 DB 이름 뒤에 `_test`를 붙여 생성합니다. 예를 들어, 실제 DB 이름이 `client_db`라면 테스트용 DB 이름은 `client_db_test`가 됩니다.
- 아래 쿼리를 순서대로 실행해 데이터베이스와 테이블, 인덱스를 생성합니다. 아래는 `client_db_test`라는 DB를 생성하는 예시 쿼리입니다. create하는 DB 이름을 변경하여 사용합니다.

```sql
-- client_db_test라는 DB 생성
CREATE DATABASE client_db_test DEFAULT CHARACTER SET = 'utf8mb4';
-- client_db_test DB를 사용해 쿼리 실행. 이래야 테이블을 해당 DB에 생성합니다.
USE client_db_test;

-- 대화내역 테이블: 대화 기록 저장, qna_dtos, user_purpose는 내역 확인용(AI에 input으로 안들어감)
CREATE TABLE `conversations` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` VARCHAR(45),
    `user_chat_id` VARCHAR(45),
    `role` VARCHAR(20),
    `qna_dtos` TEXT,
    `user_purpose` TEXT,
    `question` TEXT,
    `answer` TEXT,
    `tool_calls` TEXT,
    `tool_results` TEXT,
    `chat_type` VARCHAR(20),
    `file_types` TEXT,
    `time` TIMESTAMP DEFAULT (NOW() + INTERVAL 9 HOUR),
    PRIMARY KEY (`id`),
    INDEX `idx_user_chat_id_time` (`user_chat_id`, `time`)
);

-- 유저 데이터 테이블: 유저 정보 저장
CREATE TABLE `user_data` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` VARCHAR(45) NOT NULL,
    `user_chat_id` VARCHAR(45) NOT NULL,
    `time` TIMESTAMP DEFAULT (NOW() + INTERVAL 9 HOUR),
    `pre_messages` JSON, -- 버튼형 응대 워크플로우 메시지
    `pre_messages_summary` JSON, -- 버튼형 응대 AI요약
    `assignee` VARCHAR(64), -- 담당자 ID(담당자 배정 여부)
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_user_chat_room` (`user_id`, `user_chat_id`)
);

-- 유저 툴 사용 데이터 테이블: 툴 호출 및 결과 저장
CREATE TABLE `user_tool_data` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `user_id` VARCHAR(45),
    `user_chat_id` VARCHAR(45),
    `type` TEXT,
    `tool_name` VARCHAR(255), -- 툴 이름
    `args` TEXT, -- 호출 인자
    `return_value` TEXT, -- 반환 값
    `time` TIMESTAMP DEFAULT (NOW() + INTERVAL 9 HOUR),
    PRIMARY KEY (`id`),
    INDEX `idx_user_chat_id` (`user_chat_id`)
);

-- 메타데이터 테이블: 시스템 메타데이터 저장
CREATE TABLE `meta_data` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255),
    `value` VARCHAR(255),
    `description` VARCHAR(255),
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_data_name` (`name`)
);

-- 초기 메타데이터 삽입
INSERT INTO `meta_data` (`name`, `value`, `description`)
VALUES ('assignee', '0', '최근 배정한 담당자');
```

## OpenAI API 키 생성

### OpenAI API 키 생성

OpenAI API 키만 있으면 model은 골라서 사용할 수 있습니다. 모델명은 playground를 참고하세요.

- OpenAI playground로 이동합니다.
- 왼쪽 상단에서 Organizations: generativelab develop에서 Create project를 선택합니다.

![image](https://github.com/user-attachments/assets/6e8f52b3-d3bf-4502-88df-f0ed2ad0cb67)

- Project name을 입력하고, Create project를 누릅니다. 해당 프로젝트 명은 적절히 영어로 작성합니다.
- 프로젝트가 생성되면, 해당 프로젝트로 이동합니다.
- 오른쪽 상단의 Dashboard를 클릭합니다.
- 왼쪽 목록에서 API keys를 클릭합니다.
- 오른쪽 상단의 Create new secret key를 클릭합니다. 최초 생성 시도시 전화번호로 인증을 요구할 수 있습니다.
- Name은 영어로 적절히 입력하고, Create를 누릅니다. (Permission은 All로 되어있어야합니다.)
- 생성된 API key를 복사해둡니다. 잃어버리면 다시 생성해야 합니다.
- 해당 API key를 이용해 아무 모델이나 사용할 수 있습니다.

### Azure OpenAI API 키 생성

Azure OpenAI API 키는 관리자에게 요청해 생성합니다. 관리자가 지역, 할당량, 모델명, 엔드포인트, 키를 알려줄 것입니다.
모델명, 엔드포인트, 키를 복사해둡니다.

_생성 방법_

AI 배포를 원하는 지역으로 접근합니다.
배포를 원하는 모델을 선택하고, 이름을 지정하고 Global Standard로 할당량을 선택해 배포합니다.
컨텐츠 필터를 모두 높음으로 설정(필터링 최대한 안함)으로 설정해 만들고, 해당 모델에서 그 컨텐츠 필터를 사용하도록 합니다.
해당 배포명과 엔드포인트, 키를 이용합니다.

## AWS Lambda 설정

람다도 2개 만들어야 합니다. 하나는 실제 배포용, 다른 하나는 테스트용입니다. 각 람다에 대해 아래 설정을 진행해주세요.

### AWS Lambda 생성

- AWS Lambda 페이지로 이동합니다. 리전은 서울로 설정합니다.

![Lambda 접속 화면](https://github.com/user-attachments/assets/a971557b-fe2b-4a3a-800a-52fc93a7fa87)

- Create function(함수 생성)을 누릅니다.
- `새로 작성` 옵션을 선택합니다.(기본 설정되어있습니다)
- 함수 이름으로 1. 실제 배포용은 실제 배포용으로, 2. 테스트용은 실제 배포용 이름 + `_test`로 설정합니다.
  - 예를 들어 실제 배포용 이름이 `ai_agent`라면 테스트용 이름은 `ai_agent_test`가 됩니다.
  - 보통은 `{프로젝트}_ai_agent`가 람다 이름이 됩니다.
- 런타임은 Python 3.10을 선택합니다.
- 나머지는 기본 설정 그대로 두고 함수 생성을 누릅니다. (아키텍쳐: x86_64)

### Lambda 개요 설정

함수 개요 내에서 설정할 항목입니다.

**함수 레이어 설정**

- 함수 이름 아래 Layers를 클릭합니다. <계층> 오른쪽 끝 [Add a layer]를 클릭합니다.

- `계층 선택 > 계층 소스` 를 `사용자 지정 계층` 으로 선택합니다.
- `사용자 지정 계층` 에서 원하는 계층을 선택합니다.
- `사용자 지정 계층`을 선택한 후 생긴 `버전` 항목에서 원하는 버전을 선택합니다.
- `추가` 버튼을 눌러 계층을 추가합니다.

- 아래 두 계층은 AI 챗봇을 사용하기 위한 필수 레이어입니다.
  - HTTP 요청:
    - 사용자 지정 계층: requests
    - 버전: 2
  - OpenAI(pydantic 포함), mysql 연결, 재시도정책:
    - 사용자 지정 계층: openai_pymysql_tenacity
    - 버전: 4

최소 설정시에는 위 두 라이브러리만 있어도 충분합니다.

이외에도 구글 API 사용시 사용하는 google_api_python_client_google_auth, pdf 열람 및 생성시 사용하는 PIL / PyMuPDF / PyPDF2, 암호화 관련해 사용하는 pycryptodome, mysql만 따로 사용하기 위한 mysql 등 다양한 계층을 추가할 수 있고, 추가로 import할 라이브러리가 있을 경우 계층을 추가합니다.

**트리거 추가**

- `API 게이트웨이`를 선택합니다.
- 새 API 생성을 선택합니다.
- API 유형을 HTTP API로 둡니다.
- 보안은 `열기(open)`로 설정합니다.
- `추가` 버튼을 클릭합니다.
- API 게이트웨이로 트리거가 생성됩니다. API 엔드포인트에서 웹훅으로 사용할 URL을 확인할 수 있습니다.

### Lambda 구성 설정

- 함수 구성 설정에서 확인할 항목들입니다.

- <구성> 을 선택합니다.

**일반 구성**
오른쪽 편집 버튼을 클릭합니다.

- 설명: 이 프로젝트가 어떤 프로젝트인지 간략하게 작성합니다. 작성예시: `client 테스트 람다`
- 메모리: 기본 128MB로 설정되어 있습니다. 256MB로 설정해 메모리 초과를 방지하고, 512MB 등 필요시 조절합니다.
- 제한 시간: 기본 3초로 설정되어 있습니다. 3분으로 설정해 타임아웃을 방지하고, 필요시 조절합니다.

**환경 변수**
오른쪽 편집 버튼을 클릭합니다.
`환경 변수 추가`를 클릭해 환경 변수 수를 늘릴 수 있습니다.
아래 환경변수 설명을 참고해 추가합니다.

- `APP_ENV`: 실제 배포용은 `production`, 테스트용은 `test`로 설정합니다.

앞에서 생성한 채널톡 API 키/시크릿을 환경 변수로 추가합니다.

- `X_ACCESS_KEY`: 채널톡 키
- `X_ACCESS_SECRET`: 채널톡 시크릿

* 테스트 람다인 경우, 테스트 채널의 키/시크릿으로 설정해야 합니다.

앞에서 생성한 DB 정보를 환경 변수로 추가합니다.

- `DB_HOST`: DB 주소
- `DB_USER`: DB 유저
- `DB_PASSWORD`: DB 비밀번호
- `DB_NAME`: DB 이름

* 테스트 람다인 경우, DB_NAME에 `_test`를 붙여야 합니다.

앞에서 생성한 OpenAI API 키를 환경 변수로 추가합니다.
OpenAI 사용 시

- `CHAT_MODEL`: 기본 GPT 모델명 (보통 `gpt-4o-2024-08-06`로 설정합니다.)
- `OPENAI_API_KEYS`: OpenAI GPT 사용 시 API 키

* 테스트 람다인 경우, 테스트용 OpenAI API 키로 설정해야 합니다.

Azure OpenAI 사용 시

- `AZURE_CHAT_MODEL`: Azure GPT 사용 시 모델명 (보통 `gpt-4o-2024-08-06_{프로젝트명}`로 설정합니다.)
- `AZURE_OPENAI_API_KEYS`: Azure GPT 사용 시 API 키
- `AZURE_OPENAI_ENDPOINTS`: Azure GPT 사용 시 엔드포인트

* 테스트 람다인 경우, 테스트용 Azure OpenAI API 키로 설정해야 합니다.

## 채널톡 웹훅 연결

- 채널톡의 채널 목록에서 생성해둔 채널을 클릭합니다.
- `채널 설정 > 보안 및 개발 > 웹훅` 을 클릭합니다.
- 오른쪽 상단의 `Webhook 만들기`를 클릭합니다.
- Webhook 생성 팝업에서 다음과 같이 설정합니다.
  - 이름: `ai_agent`
  - URL: 앞에서 생성한 Lambda의 API 게이트웨이 엔드포인트 URL
  - 아래 체크박스들 중 `기타 > 유저챗 대화`만 체크합니다.
  - - 위 설정들은 언제든지 변경할 수 있습니다.
  - `확인`을 누르면, 웹훅 생성완료 팝업창으로 변경됩니다.
  - 웹훅 연결이 완료되었습니다.

## 깃허브 설정

### 깃허브 리포지토리 생성

[젠랩 깃허브 리포지토리](https://github.com/orgs/generativelab-develop/repositories) 로 이동합니다.
오른쪽 상단의 `New repository` 버튼을 누릅니다.
Create a new repository 화면에서 아래와 같이 설정합니다.

- Repository template: `No template`에서 `generativelab-develop/lambda-template-purpose`를 선택합니다.
  - Include all branches는 선택하지 않습니다.
- Owner: `generativelab-develop` 그대로 둡니다.
- Repository name: AWS Lambda의 이름으로 사용할 이름으로 지정합니다.
  - 이 이름이 AWS Lambda의 이름과 동일해야 GitHub Action이 성공적으로 작동합니다.
- Private로 설정을 그대로 두고, Create repository를 누릅니다.
- 리포지토리가 생성됩니다.

### 리포지토리 Settings 설정

- [Github AWS 키 노션 링크](https://www.notion.so/801dd3ecee1d4fe3982d0058fd3ef744?pvs=4#6873c216bfbf4ba4b4fa7411e6b39486)에서 AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY를 확인합니다.
- GitHub Repo에서 **Settings** > **Secrets and variables** > **Actions**에서 `Secrets` 화면으로 이동합니다.

![리포지토리 시크릿 화면](https://github.com/user-attachments/assets/3a7ae8e8-75bf-4397-9f34-5ee8da2d35d3)

- New repository secret을 누릅니다. `Name` 에 AWS_ACCESS_KEY_ID를, `Secret`에 AWS Access Key ID를 입력합니다. Add secret을 눌러 등록합니다.
- New repository secret을 누릅니다. `Name` 에 AWS_SECRET_ACCESS_KEY를, `Secret`에 AWS Secret Access Key를 입력합니다. Add secret을 눌러 등록합니다.

## AI 연결 확인

### 깃허브 리포지토리 복제

- github repository로 돌아갑니다. 왼쪽 상단의 `<> Code` 버튼을 눌러도 됩니다.
- 화면 중간쯤의 초록색 `<> code` 버튼을 누릅니다.
- Local > Clone > HTTPS 에서 링크가 보여집니다. 해당 링크를 복사합니다. 해당 링크는 옆의 네모 두개 겹처진 버튼을 누르면 복사됩니다.

![git clone link](https://github.com/user-attachments/assets/44ce86bc-db36-4c8b-a9be-026960404bc5)

**저는 CMD창을 잘 못다뤄요**

- 리포지토리 복제를 원하는 로컬 파일 위치로 이동합니다.
- 파일 주소창에 cmd를 입력해 해당 위치에서 터미널을 엽니다.
- `git clone {복사한 링크}`를 입력해 리포지토리를 복제합니다.
- 복제가 완료되면 복제된 폴더를 우클릭해 VSCode로 열거나, VSCode를 실행해 해당 폴더를 엽니다.

**저는 CMD 좀 만져봤어요**

- 터미널을 엽니다. VSCode에서 <code>Ctrl + `</code>를 눌러 터미널을 열거나, 윈도우버튼을 누르고 cmd를 검색해 명령 프롬프트나 파워쉘을 열어도 좋습니다.
- 리포지토리 clone을 원하는 디렉토리로 이동합니다.
- 해당 위치에서 `git clone {복사한 링크}`를 입력해 리포지토리를 복제합니다.
  - 하위 폴더가 해당 위치에 복제되는게 아니라 해당 위치에 리포지토리이름의 폴더가 생성됨에 유의합니다.
- VSCode상에서 `Ctrl + Shift + E`를 눌러 액티브바의 Explorer(탐색기)로 이동합니다.
- 빈 화면에 우클릭을 해서 `Add Folder to Workspace`를 찾아 클릭합니다.
- 방금 clone한 폴더를 선택해 추가합니다.
- 복제가 완료됩니다.

### test 브랜치 생성

- develop과 test 브랜치를 나눠서 작업해야 하기때문에, 최초에 세팅을 하고 가는 것이 좋습니다.
- 아래 커맨드를 cmd창에서 진행해 test 브랜치를 생성합니다.

```bash
cd "your_path/your_repository_name" # 복제한 리포지토리 폴더로 이동하는 명령어입니다. 잘 와있으면 안건드려도 됩니다.
git branch test develop # develop 브랜치에서 test 브랜치를 만듭니다.
git checkout test # test 브랜치로 이동합니다.
git push --set-upstream origin test # 현재 브랜치를 원격 저장소에 test라는 이름으로 생성합니다.
```

- test 브랜치를 성공적으로 github에 생성합니다.
- 템플릿 설정상 develop 브랜치에 푸쉬되는 내용은 리포지토리명과 같은 이름의 람다로, test 브랜치에 푸쉬되는 내용은 리포지토리명\_test 와 같은 이름의 람다로 배포됩니다.

### 작업 방법

**기본적으로 수정 작업 commit은 test 브랜치에서만 하고, develop브랜치는 merge만 하는 것으로 합니다.**

1. 수정사항이 있을 때

- 해당 리포지토리 경로 위치에서 커맨드 창을 엽니다. (VSCode에서 <code>Ctrl + `</code>)
- 현재 브랜치가 test 브랜치가 맞는지 `git branch`를 입력해 확인합니다.
- test 브랜치가 아니라면, `git checkout test`을 입력해 test 브랜치로 이동합니다.
- 해당 브랜치에서 `git pull`을 입력해 최신 커밋을 받아옵니다. (이미 최신 커밋이면 생략 가능)
- 이후 작업을 진행합니다.

2. 수정사항을 commit하려 할 때

- `git add .` 을 입력해 저장시킬 변경사항을 추가합니다.
- `git commit -m "변경사항 내용"` 으로 커밋합니다. 변경사항 내용은 변경사항에 맞게 작성합니다.
- `git push`를 입력해 변경사항을 깃허브의 해당 브랜치에 푸쉬합니다.
- Github Actions로 자동으로 배포가 진행됩니다.
- 깃허브 레포지토리 페이지로 돌아가 상단의 Actions 탭을 클릭합니다.
- 방금 커밋한 이름의 작업이 초록색 체크표시가 되면 성공적으로 배포가 완료된 것입니다.
  - 노란색으로 돌고있으면 배포가 진행중입니다.
  - 빨간색 엑스표시가 되면 배포에 실패한 것입니다.

3. 수정사항을 develop 브랜치(실제 배포 환경)에 반영하려 할 때
   test 브랜치에서 작업한 내용을 develop에 모두 반영하는 작업입니다.

- `git checkout develop`을 입력해 develop 브랜치로 이동합니다.
- `git pull`을 입력해 develop 브랜치의 최신 커밋을 받아옵니다. (이미 최신 커밋이면 생략 가능)
- `git merge test`를 입력해 test 브랜치의 변경사항을 develop 브랜치에 반영합니다.
- `git push`를 입력해 develop 브랜치에 반영한 변경사항을 깃허브에 푸쉬합니다.
- Github Actions가 자동으로 배포를 진행합니다. 진행 현황은 위와 같이 확인합니다.

4. **긴급 수정사항**이 발생해 develop 브랜치에 바로 반영해야 할 때 / test 브랜치에서 **작업중인 내역이 있는데 아직 완료되지 않았**을 때 추가작업 진행시
   수정사항을 바로 develop에 반영하고, 이 내용을 test에 반영합니다.
   괜히 양쪽 브랜치에서 다 checkout해서 작업하지 마십시오.
   conflict 나니까 골머리 앓는 자신을 볼 수 있을겁니다.
   꼭 merge로 반영하세요.

- `git checkout develop`을 입력해 develop 브랜치로 이동합니다.
- `git pull`을 입력해 develop 브랜치의 최신 커밋을 받아옵니다. (이미 최신 커밋이면 생략 가능)
- 수정사항 작업을 진행합니다.
- `git add .` 을 입력해 저장시킬 변경사항을 추가합니다.
- `git commit -m "변경사항 내용"` 으로 커밋합니다. 변경사항 내용은 변경사항에 맞게 작성합니다.
- `git push`를 입력해 변경사항을 깃허브의 develop 브랜치에 반영합니다.
- Github Actions로 자동으로 배포가 진행됩니다.
- `git checkout test`을 입력해 test 브랜치로 이동합니다.
- `git merge develop`를 입력해 develop 브랜치의 변경사항을 test 브랜치에 반영합니다. conflict가 발생할 경우, 화이팅하세요.
- `git push`를 입력해 test 브랜치에 반영한 변경사항을 깃허브에 푸쉬합니다.

## test.py 사용 방법

- 해당 프로젝트에서 사용하는 모듈들을 전부 pip install합니다.
- 레포지토리 루트 폴더에 .env 파일을 생성하고, 해당 파일에 원하는 환경변수를 넣습니다.
- test.py를 실행하고, return값을 확인합니다.

# 템플릿 구조

## client

각 클라이언트와 해당 유틸리티

- **ai_client**: OpenAI를 다루는 클라이언트
  - **prompts**: 파일별로 프롬프트 작성 후 **init**에서 import합니다.
  - **tools**: 각 파일별로 AI별 Tool 작성 후 **init**에서 import합니다.
- **db_client**: DB 클라이언트. `BaseDBClient`를 상속받아 사용합니다.
- **talk_client**: 채널톡과 연결을 다루는 클라이언트로, 채널톡에서 발생하는 오류를 처리합니다.

- **pre_processor**: 채팅 데이터 전처리 클라이언트입니다.
- **context_extractor**: 채팅 데이터에서 필요한 정보(user_conversation, user_purpose, qua_dtos)를 추출합니다.
- **chat_manager**: `chat_handler`의 하위 클라이언트로, AI의 채팅 부분(답변, 답변기록, toolcall 호출)을 담당합니다.
- **tool_call_resolver**: tool_call을 해석하고 실행합니다.

- **chat_handler**: 전반적인 채팅 처리 클라이언트로, 전처리/맥락파악/채팅/toolcall 총 과정을 총괄합니다.

## utils

- custom_exception: 커스텀 예외처리 parent class
- holidays_KR: 한국 공휴일 정보

- **chat_data**: 이번 채팅 데이터를 파싱하고 답변 과정을 트래킹합니다.
- **meta_data**: qna 생성에 관여하는 데이터를 관리합니다.

  - client_data: chat_data에서 가져올 수 있는 정보
  - db_data: user_data 테이블에서 가져오는 정보
  - tool_call_data: 채팅방 함수 호출 정보. user_tool_data 테이블에서 가져옴

- **time_info**: 시간 관련 정보 통합 처리 모듈
