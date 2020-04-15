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


class UnableToBuildAudioFileException(ClientException):
    '''Exception that's thrown when when the bot is unable to build an audio file for playback.'''

    def __init__(self, message):
        super(UnableToBuildAudioFileException, self).__init__(message)


class BuildingAudioFileTimedOutExeption(UnableToBuildAudioFileException):
    '''
    Exception that's thrown when when the audio generation logic times out.
    See: https://github.com/naschorr/hawking/issues/50
    '''

    def __init__(self, message):
        super(BuildingAudioFileTimedOutExeption, self).__init__(message)


class MessageTooLongException(UnableToBuildAudioFileException):
    '''Exception that's thrown during the audio file build process when the user's message is too long'''

    def __init__(self, message):
        super(MessageTooLongException, self).__init__(message)
