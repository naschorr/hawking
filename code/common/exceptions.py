import inspect

from discord.errors import ClientException

class UnableToConnectToVoiceChannelException(ClientException):
    '''
    Exception that's thrown when the client is unable to connect to a voice channel
    '''

    def __init__(self, message, channel, **kwargs):
        super(UnableToConnectToVoiceChannelException, self).__init__(message)

        self._channel = channel
        self._can_connect = kwargs.get('connect', False)
        self._can_speak = kwargs.get('speak', False)

    @property
    def channel(self):
        return self._channel


    @property
    def can_connect(self):
        return self._can_connect


    @property
    def can_speak(self):
        return self._can_speak


class WillNotConnectToVoiceChannelException(ClientException):
    '''
    Exception that's thrown when the specified voice channel will not be connected to, as it's out of scope or it doesn't exist
    '''

    def __init__(self, message, channel, **kwargs):
        super(WillNotConnectToVoiceChannelException, self).__init__(message)

        self._channel = channel

    @property
    def channel(self):
        return self._channel


class UnableToStoreInDatabaseException(RuntimeError):
    '''
    Exception that's thrown when the database store operation failed for some reason.
    '''

    def __init__(self, message: str):
        super(UnableToStoreInDatabaseException).__init__(message)


class ModuleLoadException(RuntimeError):
    '''
    Exception that's thrown when a module fails to load (implicitly at runtime).
    '''

    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)

        self._module_name = inspect.stack()[1].frame.f_locals['self'].__class__.__name__
        self._message = message
        self._cause = cause


    def __str__(self):
        strings = [f"Unable to load module '{self._module_name}', '{self._message}'"]
        if (self._cause):
            strings.append(f"Caused by: {self._cause}")

        return '. '.join(strings)


    @property
    def module_name(self):
        return self._module_name


    @property
    def message(self):
        return self._message


    @property
    def cause(self):
        return self._cause
