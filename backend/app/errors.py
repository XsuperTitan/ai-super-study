class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, detail: object | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


class ModelAdapterError(Exception):
    pass
