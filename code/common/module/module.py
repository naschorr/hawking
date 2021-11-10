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
        self._after_successful_init = kwargs.get('after_successful_init')
        self._after_failed_init = kwargs.get('after_failed_init')

    ## Properties

    @property
    def successful(self) -> bool:
        return self._successful

    @successful.setter
    def successful(self, value: bool):
        self._successful = value

        if (value and self.after_successful_init is not None):
            self.after_successful_init()
        elif (not value and self.after_failed_init is not None):
            self.after_failed_init()


    @property
    def after_successful_init(self) -> Callable[[], None]:
        return self._after_successful_init


    @after_successful_init.setter
    def after_successful_init(self, value: Callable[[], None]):
        self._after_successful_init = value


    @property
    def after_failed_init(self) -> Callable[[], None]:
        return self._after_failed_init

    
    @after_failed_init.setter
    def after_failed_init(self, value: Callable[[], None]):
        self._after_failed_init = value


class Cog(Module, commands.Cog):
    pass