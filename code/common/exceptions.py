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


class AlreadyInVoiceChannelException(ClientException):
    '''
    Exception that's thrown when the client is already in the destination voice channel. Usually happens due to
    disconnecting the bot while connected, and reconnecting before the bot can time out.
    '''

    def __init__(self, message, channel):
        super(AlreadyInVoiceChannelException, self).__init__(message)

        self._channel = channel


    @property
    def channel(self):
        return self._channel