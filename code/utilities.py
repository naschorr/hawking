import os
import sys
import json

## Config
CONFIG_OPTIONS = {}         # This'll be populated on import
DEBUG_LEVEL_KEY = "debug_level"
CONFIG_NAME = "config.json"	# The name of the config file
DIRS_FROM_ROOT = 1			# How many directories away this script is from the root
PLATFORM = sys.platform


def get_root_path():
	## -1 includes this script itself in the realpath
	return os.sep.join(os.path.realpath(__file__).split(os.path.sep)[:(-1 - DIRS_FROM_ROOT)])


def load_json(path):
    with open(path) as fd:
        return json.load(fd)


def load_config():
	return load_json(os.sep.join([get_root_path(), CONFIG_NAME]))


def debug_print(*args, **kwargs):
    """debug_print
    Print the debug statement only if that statement's supplied debug_level kwarg is less than the
    debug_level specified in config.json.
    Commonly used levels:
    0 - Extremely important, usually for extreme exceptions where something huge is going wrong
    1 - Important, usually for exceptions that really shouldn't be happening, but probably won't
        immediately tank the system
    2 - Slightly important, usually for small exceptions that won't affect operation
    3 - Not at all important, usually just for warnings
    4 - For debugging only
    """

    ## Read and clean up the kwargs that'll be passed onto the print function
    debug_print_level = kwargs.get(DEBUG_LEVEL_KEY, 0)
    if(DEBUG_LEVEL_KEY in kwargs):
        del kwargs[DEBUG_LEVEL_KEY]

    ## Compare and print the message if necessary
    if(debug_print_level <= CONFIG_OPTIONS.get(DEBUG_LEVEL_KEY, 0)):
        print(*args, **kwargs)


def is_linux():
    return ("linux" in PLATFORM)


def is_windows():
    return ("win" in PLATFORM)


CONFIG_OPTIONS = load_config()
