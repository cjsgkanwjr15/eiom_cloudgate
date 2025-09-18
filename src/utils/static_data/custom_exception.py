class CustomException(Exception):
    def __init__(self, error_code):
        super().__init__(error_code)
        self.error_name = error_code.name
        self.error_code = error_code.value["code"]
        self.message = error_code.value["message"]

    def print_error(self):
        print(
            f"Exception: {self.error_name}, Code: {self.error_code}, Message: {self.message}"
        )
