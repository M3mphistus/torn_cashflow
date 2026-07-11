class ApiError(Exception):
    def __init__(self, status_code: int, message: str, code: str, torn_error_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.torn_error_code = torn_error_code
