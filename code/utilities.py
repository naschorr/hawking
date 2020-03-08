import os
import sys
import json
import logging
import pathlib
from logging.handlers import RotatingFileHandler

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


def is_linux():
    return ("linux" in PLATFORM)


def is_windows():
    return ("win" in PLATFORM)


def initialize_logging(logger):
    FORMAT = "%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(FORMAT)
    logging.basicConfig(format=FORMAT)

    log_level = str(CONFIG_OPTIONS.get("log_level", "DEBUG"))
    if (log_level == "DEBUG"):
        logger.setLevel(logging.DEBUG)
    elif (log_level == "INFO"):
        logger.setLevel(logging.INFO)
    elif (log_level == "WARNING"):
        logger.setLevel(logging.WARNING)
    elif (log_level == "ERROR"):
        logger.setLevel(logging.ERROR)
    elif (log_level == "CRITICAL"):
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.DEBUG)

    ## Get the directory containing the logs and make sure it exists, creating it if it doesn't
    log_dir = CONFIG_OPTIONS.get("log_dir", os.path.sep.join([get_root_path(), "logs"]))
    pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)    # Basically a mkdir -p $log_dir

    log_path = os.path.sep.join([log_dir, "clipster.log"])

    ## Setup and add the rotating log handler to the logger
    max_bytes = CONFIG_OPTIONS.get("log_max_bytes", 1024 * 1024 * 10)   # 10 MB
    backup_count = CONFIG_OPTIONS.get("log_backup_count", 10)
    rotating_log_handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
    rotating_log_handler.setFormatter(formatter)
    logger.addHandler(rotating_log_handler)

    return logger


CONFIG_OPTIONS = load_config()
