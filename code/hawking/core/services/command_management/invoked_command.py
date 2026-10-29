class InvokedCommand:
    def __init__(
            self,
            successful: bool = True,
            error: Exception | None = None,
            human_readable_error_message: str | None = None
    ):
        self._successful: bool = successful
        self._error: Exception | None = error
        self._human_readable_error_message: str | None = human_readable_error_message

    ## Properties

    @property
    def successful(self) -> bool:
        return self._successful


    @property
    def error(self) -> Exception | None:
        return self._error


    @property
    def human_readable_error_message(self) -> str | None:
        return self._human_readable_error_message
