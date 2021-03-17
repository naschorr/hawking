from discord.ext import commands

class DiscoverableModule():
    '''
    This really should be an abstract class, but there are some issues with multiple inheritance of meta classes
    (ABCMeta and CogMeta). Until that gets fixed, I'll just have to live with this plain old class.
    '''

    def __init__(self):
        if (self is DiscoverableModule or self is DiscoverableCog or self is DiscoverableDefaultHelpCommand):
            raise TypeError('{} should be treated as abstract, and shouldn\'t be directly instantiated.'.format(self.__class__.__name__))

        self._successful = None

    ## Properties

    @property
    def successful(self) -> bool:
        return self._successful

    @successful.setter
    def successful(self, value: bool):
        self._successful = value


class DiscoverableCog(DiscoverableModule, commands.Cog):
    pass


class DiscoverableDefaultHelpCommand(DiscoverableModule, commands.DefaultHelpCommand):
    pass
