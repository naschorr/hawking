from discord.ext import commands

class DiscoverableModule():
    def __init__(self):
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
