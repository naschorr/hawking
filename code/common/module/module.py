from typing import Callable

from discord.ext import commands

class Module():
    '''
    This really should be an abstract class, but there are some issues with multiple inheritance of meta classes
    (ABCMeta and CogMeta). Until that gets fixed, I'll just have to live with this plain old class.
    '''

    def __init__(self, *args, **kwargs):
        if (self is Module or self is Cog):
            raise TypeError('{} should be treated as abstract, and shouldn\'t be directly instantiated.'.format(self.__class__.__name__))

        self._successful = None
        self._afterSuccessfulInit = kwargs.get('afterSuccessfulInit')
        self._afterFailedInit = kwargs.get('afterFailedInit')

    ## Properties

    @property
    def successful(self) -> bool:
        return self._successful

    @successful.setter
    def successful(self, value: bool):
        self._successful = value

        if (value and self.afterSuccessfulInit is not None):
            self.afterSuccessfulInit()
        elif (not value and self.afterFailedInit is not None):
            self.afterFailedInit()


    @property
    def afterSuccessfulInit(self) -> Callable[[], None]:
        return self._afterSuccessfulInit


    @afterSuccessfulInit.setter
    def afterSuccessfulInit(self, value: Callable[[], None]):
        self._afterSuccessfulInit = value


    @property
    def afterFailedInit(self) -> Callable[[], None]:
        return self._afterFailedInit

    
    @afterFailedInit.setter
    def afterFailedInit(self, value: Callable[[], None]):
        self._afterFailedInit = value


class Cog(Module, commands.Cog):
    pass
