from hawking.core.services.module_manager.module import Cog, Module


class DiscoverableModule(Module):
    pass


class DiscoverableCog(DiscoverableModule, Cog):
    pass
