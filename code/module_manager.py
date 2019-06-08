import os
import sys
import importlib
import inspect
from collections import OrderedDict

import utilities

## Config
CONFIG_OPTIONS = utilities.load_config()


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
    ## Keys
    MODULES_FOLDER_KEY = "modules_folder"

    def __init__(self, hawking, bot):
        self.modules_folder = CONFIG_OPTIONS.get(self.MODULES_FOLDER_KEY, "")

        self.hawking = hawking
        self.bot = bot
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


    ## Finds and registers modules inside the modules folder
    def discover(self):
        ## Assumes that the modules folder is inside the root
        modules_folder_path = os.path.abspath(os.path.sep.join(["..", self.modules_folder]))
        ## Expose the modules folder to the interpreter, so modules can be loaded
        sys.path.append(modules_folder_path)

        ## Build a list of potential module paths and iterate through it...
        candidate_modules = os.listdir(modules_folder_path)
        for candidate in candidate_modules:
            ## If the file could be a python file...
            if(candidate[-3:] == ".py"):
                name = candidate[:-3]

                ## Attempt to import the module (akin to 'import [name]') and register it normally
                ## NOTE: Modules MUST have a 'main()' function that essentially returns a list containing all the args
                ##       needed by the 'register()' method of this ModuleManager class. At a minimum this list MUST
                ##       contain a reference to the class that serves as an entry point to the module. You should also
                ##       specify whether or not a given module is a cog (for discord.py) or not.
                try:
                    module = importlib.import_module(name)
                    declarations = module.main()

                    ## Validate the shape of the main() method's data, and attempt to tolerate poor formatting
                    if(not isinstance(declarations, list)):
                        declarations = [declarations]
                    elif(len(declarations) == 0):
                        raise RuntimeError("Module '{}' main() returned empty list. Needs a class object at minimum.".format(module.__name__))

                    self.register(*declarations)
                except Exception as e:
                    utilities.debug_print("Unable to import module: {},".format(name), e, debug_level=2)
                    del module


    ## Reimport a single module
    def _reimport_module(self, module):
        try:
            importlib.reload(module)
        except Exception as e:
            print("Error: ({}) reloading module: {}".format(e, module))
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
                print("Error: {} when reloading cog: {}".format(e, module_name))
            else:
                counter += 1

        print("Loaded {}/{} cogs.".format(counter, len(self.modules)))
        return counter
