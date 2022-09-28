class InvokedCommand:
    def __init__(self, successful: bool = True, error: Exception = None, human_readable_error_message: str = None):
        self._successful: bool = successful
        self._error: Exception | None = error
        self._human_readable_error_message: str | None = human_readable_error_message

    ## Properties

    @property
    def successful(self) -> bool:
        return self._successful


    @property
    def error(self) -> Exception:
        return self._error


    @property
    def human_readable_error_message(self) -> str:
        return self._human_readable_error_message
