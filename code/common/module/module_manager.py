import os
import sys
import logging
import importlib
import asyncio
from collections import OrderedDict
from pathlib import Path
from functools import reduce

from common import utilities
from common.configuration import Configuration
from common.exceptions import ModuleLoadException
from common.logging import Logging
from common.module.module import Module
from .dependency_graph import DependencyGraph
from .module_initialization_container import ModuleInitializationContainer

from discord.ext import commands

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class ModuleEntry:
    def __init__(self, cls: Module, *init_args, **init_kwargs):
        self.module = sys.modules[cls.__module__]
        self.cls = cls
        self.name = cls.__name__
        self.is_cog = issubclass(cls, commands.Cog)
        self.args = init_args
        self.kwargs = init_kwargs

        self.dependencies = init_kwargs.get('dependencies', [])
        if ('dependencies' in init_kwargs):
            del init_kwargs['dependencies']

    ## Methods

    def get_class_callable(self) -> Module:
        '''Returns an invokable object to instantiate the class defined in self.cls'''
        return getattr(self.module, self.name)


class ModuleManager:
    '''
    Manages the modules' lifecycle. Chiefly, the discovery, registration, and installation of modules. It'll also
    support reloading existing modules/cogs too.
    '''

    def __init__(self, bot_controller, bot: commands.Bot):
        self.bot_controller = bot_controller
        self.bot = bot

        modules_dir_path = CONFIG_OPTIONS.get('modules_dir_path')
        if (modules_dir_path):
            self.modules_dir_path = Path(modules_dir_path)
        else:
            self.modules_dir_path = Path.joinpath(
                utilities.get_root_path(),
                CONFIG_OPTIONS.get('modules_dir', 'modules')
            )

        self.modules = OrderedDict()
        self.loaded_modules = {}    # Keep non-cog modules loaded in memory
        self._dependency_graph = DependencyGraph()

    ## Methods

    async def _load_module(self, module_entry: ModuleEntry, module_dependencies: list = None) -> bool:
        if(self.bot.get_cog(module_entry.name)):
            LOGGER.warn(f"Cog with name '{module_entry.name}' has already been loaded onto the bot, skipping...")
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
            LOGGER.error(f"Error: '{e.message}' while loading module: {module_entry.name}.")

            ## Only set the unsuccessful state if it hasn't already been set. Setting the successful state happens later
            if (
                    instantiated_module is not None
                    or hasattr(instantiated_module, 'successful')
                    and instantiated_module.successful is not False
            ):
                instantiated_module.successful = False
            return False

        if (module_entry.is_cog):
            await self.bot.add_cog(instantiated_module)

        self.loaded_modules[module_entry.name] = instantiated_module
        LOGGER.info(f"Instantiated {'Cog' if module_entry.is_cog else 'Module'}: {module_entry.name}")

        return True


    async def load_registered_modules(self) -> int:
        '''Performs the initial load of modules, and adds them to the bot'''

        async def load_node(node) -> int:
            counter = 0

            if (not node.loaded and reduce(lambda value, node: node.loaded and value, node.parents, True)):
                dependencies = {}
                for parent in node.parents:
                    dependencies[parent.name] = self.loaded_modules[parent.name]

                module_entry = self.modules.get(node.name)
                node.loaded = await self._load_module(module_entry, module_dependencies=dependencies)

                if (not node.loaded):
                    return 0

                ## Default the success state to True when loading a module, as that's kind of the default state. If a
                ## failure state is entered, than that's much more explicit.
                loaded_module = self.loaded_modules[module_entry.name]
                if (loaded_module.successful is None):
                    loaded_module.successful = True

                counter += 1

            for child in node.children:
                counter += await load_node(child)

            ## Number of loaded modules + the root node itself
            return counter


        ## Clear out the loaded_modules (if any)
        self.loaded_modules = {}
        self._dependency_graph.set_graph_loaded_state(False)

        ## Keep track of the number of successfully loaded modules
        counter = 0

        ## todo: parallelize?
        for node in self._dependency_graph.roots:
            try:
                counter += await load_node(node)
            except ModuleLoadException as e:
                LOGGER.warn(f"{e}. This module and all modules that depend on it will be skipped.")
                continue

        return counter


    async def reload_registered_modules(self) -> int:
        module_entry: ModuleEntry
        for module_entry in self.modules.values():
            ## Detach loaded cogs
            await self.bot.remove_cog(module_entry.name)

            ## Reimport the module itself
            try:
                importlib.reload(module_entry.module)
            except Exception as e:
                LOGGER.error(f"Error reloading module: {module_entry.name}. Attempting to continue...", e)

        ## Reload the modules via dependency graph
        loaded_module_count = await self.load_registered_modules()
        LOGGER.info(f"Loaded {loaded_module_count}/{len(self.modules)} modules.")

        return loaded_module_count


    def register_module(self, cls: Module, *init_args, **init_kwargs):
        '''Registers module data with the ModuleManager, and prepares any necessary dependencies'''

        module_entry = ModuleEntry(cls, *init_args, **init_kwargs)
        self.modules[module_entry.name] = module_entry

        self._dependency_graph.insert(cls.__name__, module_entry.dependencies)


    def discover_modules(self):
        '''Discovers the available modules, and assembles the data needed to register them'''

        if (not self.modules_dir_path.exists):
            LOGGER.warn('Modules directory doesn\'t exist, so no modules will be loaded.')
            return

        ## Build a list of potential module paths and iterate through it...
        module_directories = os.listdir(self.modules_dir_path)
        for module_directory in module_directories:
            module_path = Path.joinpath(self.modules_dir_path, module_directory)

            ## Note that the entrypoint for the module should share the same name as it's parent folder. For example:
            ## phrases.py is the entrypoint for the phrases/ directory
            module_entrypoint = Path.joinpath(module_path, module_path.name + '.py')

            if (module_entrypoint.exists):
                ## Expose the module's root directory to the interpreter, so it can be imported
                sys.path.append(str(module_path))

                ## Attempt to import the module (akin to 'import [name]') and register it normally
                ## NOTE: Modules MUST have a 'main()' function that essentially returns a list containing all the args
                ##       needed by the 'register()' method of this ModuleManager class. At a minimum this list MUST
                ##       contain a reference to the class that serves as an entry point to the module. You should also
                ##       specify whether or not a given module is a cog (for discord.py) or not.
                try:
                    module = importlib.import_module(module_path.name)
                    module_init = module.main()
                except Exception as e:
                    LOGGER.exception(f"Unable to import module {module_path.name} on bot.", e)
                    del sys.path[-1]    ## Prune back the failed module from the path
                    continue

                ## Filter out any malformed modules
                if (not isinstance(module_init, ModuleInitializationContainer) and type(module_init) != bool):
                    LOGGER.exception(
                        f"Unable to add module {module_path.name}, as it's neither an instance of {ModuleInitializationContainer.__name__}, nor a boolean."
                    )
                    continue

                ## Allow modules to be skipped if they're in a falsy 'disabled' state
                if (module_init == False):
                    LOGGER.info(f"Skipping module {module_path.name}, as its initialization data was false")
                    continue

                ## Build args to register the module
                register_module_args = []
                register_module_kwargs = {**module_init.init_kwargs}

                if (module_init.is_cog):
                    ## Cogs will need a reference to the bot
                    register_module_args.append(self.bot)
                else:
                    ## Otherwise, modules can use them as needed
                    register_module_kwargs['bot_controller'] = self.bot_controller
                    register_module_kwargs['bot'] = self.bot

                if (len(module_init.init_args) > 0):
                    register_module_args.append(*module_init.init_args)

                ## Register the module!
                try:
                    self.register_module(module_init.cls, *register_module_args, **register_module_kwargs)
                except Exception as e:
                    LOGGER.exception(f"Unable to register module {module_path.name} on bot.")
                    del sys.path[-1]    ## Prune back the failed module from the path
                    del module


    def get_module(self, name: str) -> Module | None:
        '''Gets the instance of a loaded module'''

        return self.loaded_modules.get(name)
