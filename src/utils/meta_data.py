class MetaData:
    """chat data, db.user_data, db.user_tool_data를 저장해 각 qna가 metadata를 참고해 변형될 수 있도록 함"""

    def __init__(self, metadata: dict = {}):
        self.client_data = metadata.get("client_data", {})
        self.db_data = metadata.get("db_data", {})
        self.tool_call_data = metadata.get("tool_call_data", {})

    def __str__(self):
        return f"MetaData: {self.client_data}, {self.db_data}, {self.tool_call_data}"
