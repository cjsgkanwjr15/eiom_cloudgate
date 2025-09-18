import pymysql, json
from time import sleep

from .exceptions import DBException, DBErrorCode
from src.utils import ChatData


class MysqlClient:
    """SQL과 직접 소통하는 클래스

    user_id랑 user_chat_id로 검색해서 채팅방 자체를 구분하도록 설계됨
    필요시 user_id로만 구분하도록 로직 변경 필요"""

    def __init__(self, chat_data: ChatData, db_host, db_user, db_password, db_name):
        self.chat_data: ChatData = chat_data
        self.connection = pymysql.connect(
            host=db_host, user=db_user, password=db_password, database=db_name
        )
        self.cursor = self.connection.cursor()

        self.default_hours = 24
        self.default_limit = None

    """
    *********************************************
    conversations Table
    *********************************************
    """

    def set_default_limit(self, hours=None, limit=None):
        self.default_hours = hours or self.default_hours
        self.default_limit = limit or self.default_limit

    def is_tool_call_processing(self, cursor, hours=None, limit=None):
        hours = hours or self.default_hours
        limit = limit or self.default_limit
        """tool_call이 진행중인지 확인"""
        sql = """SELECT EXISTS(
            SELECT 1
            FROM conversations
            WHERE user_id = %s AND user_chat_id = %s
                AND tool_calls IS NOT NULL
                AND tool_results IS NULL"""
        val = (self.chat_data.user_id, self.chat_data.user_chat_id)
        if hours is not None:
            sql += "\nAND time > NOW() - INTERVAL %s HOUR"
            val += (hours - 9,)
        sql += "\nORDER BY time DESC"
        if limit is not None:
            sql += "\nLIMIT %s"
            val += (limit,)
        sql += ")"
        cursor.execute(sql, val)
        row = cursor.fetchone()
        return row[0] != 0

    def add_tool_conversation(self):
        """tool 작동 후 conversation 추가"""
        try:
            with self.connection.cursor() as cursor:
                self.connection.begin()

                if self.detect_new_chat_trans(cursor):
                    return False

                conversation_id = self.add_conversation(
                    cursor,
                    {"question": "", "chat_type": "text", "file_types": None},
                )
                self.connection.commit()

                return conversation_id
        except Exception as e:
            self.connection.rollback()
            raise DBException(DBErrorCode.UNKNOWN_ERROR) from e

    def add_conversation(self, cursor, args: dict):
        """conversation 추가"""
        sql = "INSERT INTO conversations (user_id, user_chat_id, role, question, chat_type, file_types) VALUES (%s, %s, %s, %s, %s, %s)"
        file_types = (
            json.dumps(args.get("file_types"))
            if args.get("chat_type") == "files"
            else None
        )
        val = (
            self.chat_data.user_id,
            self.chat_data.user_chat_id,
            self.chat_data.role,
            args.get("question"),
            args.get("chat_type"),
            file_types,
        )
        cursor.execute(sql, val)

        return cursor.lastrowid

    def is_question_null(self, cursor, hours=None, limit=None):
        hours = hours or self.default_hours
        limit = limit or self.default_limit
        sql = "SELECT question FROM conversations WHERE user_id = %s AND user_chat_id = %s"
        val = (self.chat_data.user_id, self.chat_data.user_chat_id)
        if hours is not None:
            sql += "\nAND time > NOW() - INTERVAL %s HOUR"
            val += (hours - 9,)
        sql += "\nORDER BY time DESC LIMIT %s"
        val += (3,) if limit is None else (min(limit, 3),)

        cursor.execute(sql, val)
        return cursor.fetchall()

    def get_conversation(self, cursor, hours=None, limit=None):
        hours = hours or self.default_hours
        limit = limit or self.default_limit
        """user의 채팅만 가져다 씀"""

        sql = """SELECT
            user_id,
            user_chat_id,
            role,
            question,
            answer,
            tool_calls,
            tool_results,
            chat_type,
            file_types,
            time
        FROM conversations
        WHERE user_id = %s AND user_chat_id = %s"""
        val = (self.chat_data.user_id, self.chat_data.user_chat_id)
        if hours is not None:
            sql += "\nAND time > NOW() - INTERVAL %s HOUR"
            val += (hours - 9,)
        sql += "\nORDER BY time DESC"
        if limit is not None:
            sql += "\nLIMIT %s"
            val += (limit,)

        cursor.execute(sql, val)
        return cursor.fetchall()

    def setting_transaction(self, hours=None, limit=None, polling=3):
        hours = hours or self.default_hours
        limit = limit or self.default_limit
        print("mysql_setting_transaction 실행")
        try:
            with self.connection.cursor() as cursor:
                self.connection.begin()

                if self.is_tool_call_processing(cursor, hours, limit):
                    raise DBException(DBErrorCode.TOOL_RESULT_NOT_RECORDED)

                # 이번 대화내역 저장
                conversation_id = self.add_conversation(
                    cursor,
                    {
                        "question": self.chat_data.user_chat,
                        "chat_type": self.chat_data.chat_type,
                        "file_types": self.chat_data.file_types,
                    },
                )
                self.chat_data.set_conversation_id(conversation_id)

                # 이 polling 부분은 이전에 이미지->텍스트 처리를 AI로 돌려서 question이 null인 상황은 해당 이유로 아직 question 컬럼이 아직 작성되지 않은 상태임을 나타냄. question이 null이 아닌 공문자열인 경우는 toolcall인 케이스를 포함함
                for _ in range(polling):
                    rows = self.is_question_null(cursor, hours, limit)

                    for row in rows:
                        if row[0] is None:
                            sleep(3)
                        else:
                            break

                messages = list(reversed(self.get_conversation(cursor, hours, limit)))

                self.connection.commit()

                return messages
        except DBException:
            self.connection.rollback()
            raise
        except Exception as e:
            self.connection.rollback()
            raise DBException(DBErrorCode.UNKNOWN_ERROR) from e

    def write_tool_calls_trans(self, cursor, conversation_id, call_requests_json):
        print("mysql_write_tool_calls_trans 실행")
        sql = "UPDATE conversations SET tool_calls = %s WHERE id = %s"
        val = (call_requests_json, conversation_id)
        cursor.execute(sql, val)

    def write_tool_calls(self, call_requests_json):
        print("mysql_write_tool_calls 실행")
        try:
            with self.connection.cursor() as cursor:
                self.connection.begin()
                # 새채팅 없을때만 작동
                if self.detect_new_chat_trans(cursor):
                    raise DBException(DBErrorCode.NEW_CHAT_DETECTED)

                self.write_tool_calls_trans(
                    cursor, self.chat_data.conversation_id, call_requests_json
                )

                self.connection.commit()

                return True
        except DBException:
            self.connection.rollback()
            return False
        except Exception as e:
            self.connection.rollback()
            raise DBException(DBErrorCode.UNKNOWN_ERROR) from e

    def update_conversation_item(self, item, context):
        """conversation id로 item 컬럼 업데이트"""
        print("mysql_update_conversation_item 실행")
        sql = f"UPDATE conversations SET {item} = %s WHERE id = %s"
        val = (context, self.chat_data.conversation_id)
        self.cursor.execute(sql, val)
        self.connection.commit()

    def revert_tool_call(self):
        print("mysql_revert_tool_call 실행")
        sql = "UPDATE conversations SET tool_calls = Null, tool_results = Null WHERE id = %s"
        val = (self.chat_data.conversation_id,)
        self.cursor.execute(sql, val)
        self.connection.commit()

    def detect_new_chat(self):
        sql = "SELECT id FROM conversations WHERE user_id = %s and user_chat_id = %s ORDER BY id DESC LIMIT 2"
        val = (self.chat_data.user_id, self.chat_data.user_chat_id)
        self.cursor.execute(sql, val)
        rows = self.cursor.fetchall()

        # 채팅기록이 1개밖에 없거나
        # 맨처음 채팅기록의 question이 현재 question과 같음
        if len(rows) < 2 or rows[0][0] == self.chat_data.conversation_id:
            # 새 채팅이 아님
            return False

        # 나머지 다 새로운 채팅으로 간주
        print("new chat detected:", rows[0])
        return True

    def detect_new_chat_trans(self, cursor):
        sql = "SELECT id FROM conversations WHERE user_id = %s and user_chat_id = %s ORDER BY id DESC LIMIT 2"
        val = (self.chat_data.user_id, self.chat_data.user_chat_id)
        cursor.execute(sql, val)
        rows = cursor.fetchall()

        # 채팅기록이 1개밖에 없거나
        # 맨처음 채팅기록의 question이 현재 question과 같음
        if len(rows) < 2 or rows[0][0] == self.chat_data.conversation_id:
            # 새 채팅이 아님
            return False

        # 나머지 다 새로운 채팅으로 간주
        print("new chat detected:", rows[0])
        return True

    def write_user_purpose(self, user_purpose):
        print("write_user_purpose 실행")
        sql = "UPDATE conversations SET user_purpose = %s WHERE id = %s"
        val = (user_purpose, self.chat_data.conversation_id)
        self.cursor.execute(sql, val)
        self.connection.commit()

    def write_qna_dtos(self, qna_dtos):
        print("write_qna_dtos 실행")
        sql = "UPDATE conversations SET qna_dtos = %s WHERE id = %s"
        val = (qna_dtos, self.chat_data.conversation_id)
        self.cursor.execute(sql, val)
        self.connection.commit()

    """
    *********************************************
    user_data Table
    *********************************************
    """

    def write_user_data(self, data_name, data):
        print("write_user_data 실행")

        sql = f"""
        INSERT INTO user_data (user_id, user_chat_id, {data_name})
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE {data_name} = VALUES({data_name})
        """
        val = (self.chat_data.user_id, self.chat_data.user_chat_id, data)
        self.cursor.execute(sql, val)
        self.connection.commit()

    def get_user_data(self):
        print("get_user_data 실행")
        sql = f"SELECT pre_messages, pre_messages_summary FROM user_data WHERE user_id = %s AND user_chat_id = %s"
        val = (self.chat_data.user_id, self.chat_data.user_chat_id)
        self.cursor.execute(sql, val)
        # 0: pre_messages
        return self.cursor.fetchone()

    def update_assignee(self, assignee: str):
        print("update_assignee 실행")

        # UPSERT 쿼리
        sql = """
        INSERT INTO user_data (user_id, user_chat_id, assignee)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE assignee = VALUES(assignee)
        """
        val = (self.chat_data.user_id, self.chat_data.user_chat_id, assignee)

        self.cursor.execute(sql, val)
        self.connection.commit()
        print(
            f"Assignee updated or inserted: {assignee} for user_id {self.chat_data.user_id}."
        )

    """
    *********************************************
    user_tool_data Table
    *********************************************
    """

    def write_user_tool_data(self, tool_records: list):
        print("write_user_tool_data 실행")
        sql = "INSERT INTO user_tool_data (user_id, user_chat_id,type,tool_name, args, return_value) VALUES"
        sql += ",".join([" (%s, %s, %s, %s, %s, %s)"] * len(tool_records))
        val = []
        for record in tool_records:
            val.extend(
                (
                    self.chat_data.user_id,
                    self.chat_data.user_chat_id,
                    "function",
                    record["tool_name"],
                    json.dumps(record["args"], ensure_ascii=False),
                    json.dumps(record["return_value"], ensure_ascii=False),
                )
            )
        val = tuple(val)
        print("write_user_tool_data sql:", sql)
        print("write_user_tool_data val:", val)

        self.cursor.execute(sql, val)
        self.connection.commit()

    def get_user_tool_data(self):
        print("get_user_tool_data 실행")
        sql = f"SELECT type, tool_name, args, return_value FROM user_tool_data WHERE user_id = %s AND user_chat_id = %s"
        val = (self.chat_data.user_id, self.chat_data.user_chat_id)
        self.cursor.execute(sql, val)
        return self.cursor.fetchall()

    """
    *********************************************
    meta_data Table
    *********************************************
    """

    def get_assignee_number(self):
        sql = "SELECT value FROM meta_data WHERE name='assignee'"
        self.cursor.execute(sql)
        row = self.cursor.fetchone()
        return int(row[0])

    def update_assignee_number(self, assignee_number):
        sql = "UPDATE meta_data SET value = %s WHERE name='assignee'"
        val = (assignee_number,)
        self.cursor.execute(sql, val)
        self.connection.commit()

    def get_cafe24_access_token(self):
        sql = """
        SELECT access_token 
        FROM access_refresh_tokens 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return None
