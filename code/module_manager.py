import os
import sys
import logging
import inspect
import importlib
from collections import OrderedDict
from pathlib import Path

import utilities

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
    def __init__(self, hawking, bot):
        self.hawking = hawking
        self.bot = bot

        modules_dir_path = CONFIG_OPTIONS.get('modules_dir_path')
        if (modules_dir_path):
            self.modules_dir_path = Path(modules_dir_path)
        else:
            self.modules_dir_path = Path.joinpath(utilities.get_root_path(), CONFIG_OPTIONS.get('modules_dir', 'modules'))

        self.modules = OrderedDict()

    ## Methods

    ## Registers a module, class, and args necessary to instantiate the class
    def register(self, cls, is_cog=True, *init_args, **init_kwargs):
        if(not inspect.isclass(cls)):
            raise RuntimeError("Provided class parameter '{}' isn't actually a class.".format(cls))

        if(not init_args):
            init_args = [self.hawking, self.bot]

        module_entry = ModuleEntry(cls, is_cog, *init_args, **init_kwargs)
        self.modules[module_entry.name] = module_entry

        ## Add the module to the bot (if it's a cog), provided it hasn't already been added.
        if(not self.bot.get_cog(module_entry.name) and module_entry.is_cog):
            cog_cls = module_entry.get_class_callable()
            self.bot.add_cog(cog_cls(*module_entry.args, **module_entry.kwargs))
            logger.info("Registered cog: {} on bot.".format(module_entry.name))


    ## Finds and registers modules inside the modules folder
    def discover(self):
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
                ## Expose the module directory to the interpreter, so it can be imported
                sys.path.append(str(module_path))

                ## Attempt to import the module (akin to 'import [name]') and register it normally
                ## NOTE: Modules MUST have a 'main()' function that essentially returns a list containing all the args
                ##       needed by the 'register()' method of this ModuleManager class. At a minimum this list MUST
                ##       contain a reference to the class that serves as an entry point to the module. You should also
                ##       specify whether or not a given module is a cog (for discord.py) or not.
                try:
                    module = importlib.import_module(module_path.name)
                    declarations = module.main()
                except Exception as e:
                    logger.exception("Unable to import module {} on bot.".format(module_path.name))
                    del sys.path[-1]    ## Prune back the failed module from the path
                    continue

                try:
                    ## Validate the shape of the main() method's data, and attempt to tolerate poor formatting
                    if(not isinstance(declarations, list)):
                        declarations = [declarations]
                    elif(len(declarations) == 0):
                        raise RuntimeError("Module '{}' main() returned empty list. Needs a class object at minimum.".format(module.__name__))

                    self.register(*declarations)
                except Exception as e:
                    logger.exception("Unable to register module {} on bot.".format(module_path.name))
                    del sys.path[-1]    ## Prune back the failed module from the path
                    del module


    ## Reimport a single module
    def _reimport_module(self, module):
        try:
            importlib.reload(module)
        except Exception as e:
            logger.error("Error: ({}) reloading module: {}".format(e, module))
            return False
        else:
            return True


    ## Reloads a module with the provided name
    def _reload_module(self, module_name):
        module_entry = self.modules.get(module_name)
        assert module_entry is not None

        self._reimport_module(module_entry.module)


    ## Reload a cog attached to the bot
    def _reload_cog(self, cog_name):
        module_entry = self.modules.get(cog_name)
        assert module_entry is not None

        self.bot.remove_cog(cog_name)
        self._reimport_module(module_entry.module)
        cog_cls = module_entry.get_class_callable()
        self.bot.add_cog(cog_cls(*module_entry.args, **module_entry.kwargs))


    ## Reload all of the registered modules
    def reload_all(self):
        counter = 0
        for module_name in self.modules:
            try:
                if(self.modules[module_name].is_cog):
                    self._reload_cog(module_name)
                else:
                    self._reload_module(module_name)
            except Exception as e:
                logger.error("Error: {} when reloading cog: {}".format(e, module_name))
            else:
                counter += 1

        logger.info("Loaded {}/{} cogs.".format(counter, len(self.modules)))
        return counter
