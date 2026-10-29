import sys
import logging
import importlib
from collections import OrderedDict
from pathlib import Path
from functools import reduce

from hawking.configuration import HawkingConfig
from hawking.core.exceptions import ModuleLoadException
from hawking.core.services.logging.logging_service import Logging
from hawking.core.services.module_manager.module import Module
from .dependency_graph import DependencyGraph
from .module_initialization_container import ModuleInitializationContainer

from discord.ext import commands

class ModuleEntry:
    def __init__(self, cls: type[Module], *init_args, **init_kwargs):
        self.module = sys.modules[cls.__module__]
        self.cls = cls
        self.name = cls.__qualname__
        self.is_cog = issubclass(cls, commands.Cog)
        self.args = init_args
        self.kwargs = init_kwargs

        self.dependencies = init_kwargs.get('dependencies', [])
        if ('dependencies' in init_kwargs):
            del init_kwargs['dependencies']

    ## Methods

    def get_class_callable(self) -> type[Module]:
        '''Returns an invokable object to instantiate the class defined in self.cls'''
        return getattr(self.module, self.name)


class ModuleManager:
    '''
    Manages the modules' lifecycle. Chiefly, the discovery, registration, and installation of modules. It'll also
    support reloading existing modules/cogs too.
    '''

    def __init__(self, config: HawkingConfig, bot_controller, bot: commands.Bot | commands.AutoShardedBot):
        self.logger = Logging.initialize_logging(logging.getLogger(__name__))

        self.config = config
        self.bot_controller = bot_controller
        self.bot = bot

        self.module_config = self.config.hawking.module_loader
        self.modules_dir_path = self.module_config.directory_path

        self.modules = OrderedDict()
        self.loaded_modules = {}    # Keep non-cog modules loaded in memory
        self._dependency_graph = DependencyGraph()

    ## Methods

    async def _load_module(self, module_entry: ModuleEntry, module_dependencies: list = None) -> bool:
        '''
        Instantiates a specific module. Cog flavored modules are added to the bot.

        :rtype: bool
        '''

        if(self.bot.get_cog(module_entry.name)):
            self.logger.warn(f"Cog with name '{module_entry.name}' has already been loaded onto the bot, skipping...")
            return

        module_invoker = module_entry.get_class_callable()
        instantiated_module: Module = None
        try:
            instantiated_module = module_invoker(
                *module_entry.args,
                **{'dependencies': module_dependencies or []},
                **module_entry.kwargs
            )
        except ModuleLoadException as e:
            self.logger.error(f"Error: '{e.message}' while loading module: {module_entry.name}.")
            if instantiated_module is not None and instantiated_module.successful is not False:
                instantiated_module.successful = False
            return False

        if module_entry.is_cog:
            await self.bot.add_cog(instantiated_module)

        self.loaded_modules[module_entry.name] = instantiated_module
        self.logger.info(f"Instantiated {'Cog' if module_entry.is_cog else 'Module'}: {module_entry.name}")
        return True

    async def load_registered_modules(self) -> int:
        '''Performs the initial load of modules, and adds them to the bot'''

        async def load_node(node) -> int:
            counter = 0
            if not node.loaded and reduce(lambda value, parent: parent.loaded and value, node.parents, True):
                dependencies = {parent.name: self.loaded_modules[parent.name] for parent in node.parents}
                module_entry = self.modules.get(node.name)
                node.loaded = await self._load_module(module_entry, module_dependencies=dependencies)
                if not node.loaded:
                    return 0

                loaded_module = self.loaded_modules[module_entry.name]
                if loaded_module.successful is None:
                    loaded_module.successful = True
                counter += 1

            for child in node.children:
                counter += await load_node(child)
            return counter

        self.loaded_modules = {}
        self._dependency_graph.set_graph_loaded_state(False)
        counter = 0
        for node in self._dependency_graph.roots:
            try:
                counter += await load_node(node)
            except ModuleLoadException as e:
                self.logger.warn(f"{e}. This module and all modules that depend on it will be skipped.")
        return counter

    async def reload_registered_modules(self) -> int:
        for module_entry in self.modules.values():
            await self.bot.remove_cog(module_entry.name)
            try:
                importlib.reload(module_entry.module)
            except Exception as e:
                self.logger.error(f"Error reloading module: {module_entry.name}. Attempting to continue...", exc_info=e)

        loaded_module_count = await self.load_registered_modules()
        self.logger.info(f"Loaded {loaded_module_count}/{len(self.modules)} modules.")
        return loaded_module_count

    def register_module(self, cls: type[Module], *init_args, **init_kwargs):
        module_entry = ModuleEntry(cls, *init_args, **init_kwargs)
        self.modules[module_entry.name] = module_entry
        self._dependency_graph.insert(cls.__qualname__, module_entry.dependencies)

    def discover_modules(self):
        '''Discovers the available modules, and assembles the data needed to register them'''
        if not self.modules_dir_path.is_dir():
            self.logger.warn('Modules directory doesn\'t exist, so no modules will be loaded.')
            return

        for module_path in sorted(self.modules_dir_path.iterdir()):
            if not module_path.is_dir() or module_path.name.startswith('__'):
                continue

            module_entrypoint = module_path / f"{module_path.name}.py"
            if not module_entrypoint.is_file():
                continue

            try:
                module = importlib.import_module(f"addons.{module_path.name}.{module_path.name}")
                module_init = module.main()
            except Exception as e:
                self.logger.exception(f"Unable to import module {module_path.name} on bot.", exc_info=e)
                continue

            if not isinstance(module_init, ModuleInitializationContainer) and type(module_init) != bool:
                self.logger.exception(
                    f"Unable to add module {module_path.name}, as it's neither an instance of {ModuleInitializationContainer.__name__}, nor a boolean."
                )
                continue
            if module_init is False:
                self.logger.info(f"Skipping module {module_path.name}, as its initialization data was false")
                continue

            module_config = getattr(self.config.modules, module_path.name, self.config)
            register_module_args = [module_config]
            register_module_kwargs = {**module_init.init_kwargs}
            if module_init.is_cog:
                register_module_args.append(self.bot)
            else:
                register_module_kwargs['bot_controller'] = self.bot_controller
                register_module_kwargs['bot'] = self.bot
            register_module_args.extend(module_init.init_args)

            try:
                self.register_module(module_init.cls, *register_module_args, **register_module_kwargs)
            except Exception as e:
                self.logger.exception(f"Unable to register module {module_path.name} on bot.", exc_info=e)

    def get_module(self, name: str) -> Module | None:
        return self.loaded_modules.get(name)
