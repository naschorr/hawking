from common.module.module import Cog, Module

from discord.ext import commands


class DiscoverableModule(Module):
    pass


class DiscoverableCog(DiscoverableModule, Cog):
    pass
