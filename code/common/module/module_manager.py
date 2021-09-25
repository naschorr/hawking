import os
import sys
import logging
import inspect
import importlib
from collections import OrderedDict
from pathlib import Path
from functools import reduce

from common import utilities
from common.exceptions import ModuleLoadException
from .dependency_graph import DependencyGraph
from .module_initialization_struct import ModuleInitializationStruct

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class ModuleEntry:
    def __init__(self, cls, is_cog, *init_args, **init_kwargs):
        self.module = sys.modules[cls.__module__]
        self.cls = cls
        self.name = cls.__name__
        self.is_cog = is_cog
        self.args = init_args
        self.kwargs = init_kwargs

    ## Methods

    ## Returns an invokable object to instantiate the class defined in self.cls
    def get_class_callable(self):
        return getattr(self.module, self.name)


class ModuleManager:
    '''
    Manages the modules' lifecycle. Chiefly, the discovery, registration, and installation of modules. It'll also
    support reloading existing modules/cogs too.
    '''

    def __init__(self, hawking, bot):
        self.hawking = hawking
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

    def _reimport_registered_module(self, module) -> bool:
        '''Reimports a given module'''

        try:
            importlib.reload(module)
            return True
        except Exception as e:
            logger.error("Error: ({}) reloading module: {}".format(e, module))
            return False


    def _reload_registered_module(self, module_name: str):
        '''Reloads a module matching the provided name'''

        module_entry = self.modules.get(module_name)
        assert module_entry is not None

        return self._reimport_registered_module(module_entry.module)


    def _reload_cog(self, cog_name):
        '''Reloads a cog that's already been attached to the bot'''

        module_entry = self.modules.get(cog_name)
        assert module_entry is not None

        self.bot.remove_cog(cog_name)
        self._reimport_registered_module(module_entry.module)
        cog_cls = module_entry.get_class_callable()
        self.bot.add_cog(cog_cls(*module_entry.args, **module_entry.kwargs))


    def reload_registered_modules(self):
        counter = 0
        for module_name in self.modules:
            try:
                if(self.modules[module_name].is_cog):
                    self._reload_cog(module_name)
                else:
                    self._reload_registered_module(module_name)
            except Exception as e:
                logger.error("Error: {} when reloading cog: {}".format(e, module_name))
            else:
                counter += 1

        logger.info("Loaded {}/{} cogs.".format(counter, len(self.modules)))
        return counter


    def _load_module(self, module_entry: ModuleEntry, module_dependencies = []):
        module_invoker = module_entry.get_class_callable()

        if(not self.bot.get_cog(module_entry.name) and module_entry.is_cog):
            instantiated_module = module_invoker(
                *module_entry.args,
                **{'dependencies': module_dependencies},
                **module_entry.kwargs
            )

            self.bot.add_cog(instantiated_module)
            self.loaded_modules[module_entry.name] = instantiated_module

            logger.info("Instantiated cog: {}".format(module_entry.name))
        elif (not module_entry.is_cog):
            self.loaded_modules[module_entry.name] = module_invoker(
                *module_entry.args,
                **{'dependencies': module_dependencies},
                **module_entry.kwargs
            )

            logger.info("Instantiated module: {}".format(module_entry.name))


    def load_registered_modules(self):
        '''Performs the initial load of modules, and adds them to the bot'''

        def load_node(node):
            if (not node.loaded and reduce(lambda value, node: node.loaded and value, node.parents, True)):
                dependencies = {}
                for parent in node.parents:
                    dependencies[parent.name] = self.loaded_modules[parent.name]

                module_entry = self.modules.get(node.name)
                self._load_module(module_entry, module_dependencies=dependencies)
                node.loaded = True

                ## Default the success state to True when loading a module, as that's kind of the default state. If a failure
                ## state is entered, than that's much more explicit.
                loaded_module = self.loaded_modules[module_entry.name]
                if (loaded_module.successful is None):
                    loaded_module.successful = True

            for child in node.children:
                load_node(child)

        ## Clear out the loaded_modules (if any)
        self.loaded_modules = {}
        self._dependency_graph.set_graph_loaded_state(False)

        ## todo: parallelize?
        for node in self._dependency_graph.roots:
            try:
                load_node(node)
            except ModuleLoadException as e:
                logger.warn(f"{e}. This module and all modules that depend on it will be skipped.")
                continue


    def register_module(self, cls, is_cog: bool, *init_args, **init_kwargs):
        '''Registers module data with the ModuleManager, and prepares any necessary dependencies'''

        dependencies = init_kwargs.get('dependencies', [])
        if ('dependencies' in init_kwargs):
            del init_kwargs['dependencies']

        module_entry = ModuleEntry(cls, is_cog, *init_args, **init_kwargs)
        self.modules[module_entry.name] = module_entry

        self._dependency_graph.insert(cls, dependencies)


    def discover_modules(self):
        '''Discovers the available modules, and assembles the data needed to register them'''

        if (not self.modules_dir_path.exists):
            logger.warn('Modules directory doesn\'t exist, so no modules will be loaded.')
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
                    logger.exception("Unable to import module {} on bot.".format(module_path.name), e)
                    del sys.path[-1]    ## Prune back the failed module from the path
                    continue

                ## Filter out any malformed modules
                if (not isinstance(module_init, ModuleInitializationStruct) and type(module_init) != bool):
                    logger.exception(
                        "Unable to add module {}, as it's neither an instance of {}, nor a boolean.".format(
                            module_path.name,
                            ModuleInitializationStruct.__name__
                        )
                    )

                ## Allow modules to be skipped if they're in a falsy 'disabled' state
                if (module_init == False):
                    logger.info("Skipping module {}, as it's initialization data was false".format(module_path.name))
                    continue

                ## Build register_module args
                register_module_args = [module_init.cls, module_init.is_cog]
                if (module_init.use_root_instance):
                    register_module_args.append(self.hawking)
                if (module_init.use_bot_instance):
                    register_module_args.append(self.bot)
                if (len(module_init.init_args) > 0):
                    register_module_args.append(*module_init.init_args)

                try:
                    self.register_module(*register_module_args, **module_init.init_kwargs)
                except Exception as e:
                    logger.exception("Unable to register module {} on bot.".format(module_path.name))
                    del sys.path[-1]    ## Prune back the failed module from the path
                    del module
