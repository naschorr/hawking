from inspect import isclass

from discord.ext import commands


class ModuleInitializationContainer:
    def __init__(self, cls, *init_args, **init_kwargs):
        if(not isclass(cls)):
            raise RuntimeError("Provided class parameter '{}' isn't actually a class.".format(cls))

        self.cls = cls
        self.is_cog = issubclass(cls, commands.Cog)
        self.init_args = init_args
        self.init_kwargs = init_kwargs
