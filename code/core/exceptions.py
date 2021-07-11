from discord.errors import ClientException


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
