import os
import sys
import json

## Config
CONFIG_OPTIONS = {}         # This'll be populated on import
DEBUG_KEY = "debug"
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
    if(CONFIG_OPTIONS.get(DEBUG_KEY, False)):
        print(*args, **kwargs)


def is_linux():
    return ("linux" in PLATFORM)


def is_windows():
    return ("win" in PLATFORM)


CONFIG_OPTIONS = load_config()
