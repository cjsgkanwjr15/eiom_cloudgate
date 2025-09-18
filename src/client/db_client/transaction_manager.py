from pymysql import Connection
from pymysql.cursors import DictCursor


class TransactionManager:
    """아직 사용하지 않는 트랜잭션 관리 클래스
    DictCursor을 사용해 트랜잭션을 관리할 수 있음"""

    def __init__(self, connection: Connection):
        self.connection = connection
        self.auto_commit = connection.get_autocommit()
        self.cursor: DictCursor | None = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
            print(dict(exc_type=exc_type, exc_value=exc_value, traceback=traceback))

        self.close()

    def start(self):
        """Explicitly start a transaction without using 'with'."""
        self.connection.autocommit(False)
        self.cursor = self.connection.cursor(cursor=DictCursor)

        return self.cursor

    def commit(self):
        """트랜잭션 커밋"""
        if self.connection.open:
            self.connection.commit()
        else:
            print("Connection was already closed")

    def rollback(self):
        """트랜잭션 롤백"""
        if self.connection.open:
            self.connection.rollback()
        else:
            print("Connection was already closed")

    def close(self):
        """트랜잭션 종료"""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        else:
            print("Cursor was already closed")

        self.connection.autocommit(self.auto_commit)
