import os
import sys
import datetime
import json
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

## Config
CONFIG_OPTIONS = {}                     # This'll be populated on import
CONFIG_NAME = "config.json"	            # The name of the config file
DEV_CONFIG_NAME = "config.dev.json"     # The name of the dev config file (overrides properties stored in the normal and prod config files)
PROD_CONFIG_NAME = "config.prod.json"   # The name of the prod config file (overrides properties stored in the normal config file)
DIRS_FROM_ROOT = 2			            # How many directories away this script is from the root
PLATFORM = sys.platform


def get_root_path() -> Path:
    path = Path(__file__)

    for _ in range(DIRS_FROM_ROOT + 1):  # the '+ 1' includes this script in the path
        path = path.parent

    return path


def load_json(path: Path) -> dict:
    with open(path) as fd:
        return json.load(fd)


def save_json(path: Path, data: dict):
    with open(path, 'w') as fd:
        json.dump(data, fd)


def load_config(directory_path: Path = None) -> dict:
    '''
    Parses one or more JSON configuration files to build a dictionary with proper precedence for configuring the program

    :param directory_path: Optional path to load configuration files from. If None, then the program's root (cwd/..) will be searched.
    :type directory_path: Path, optional
    :return: A dictionary containing key-value pairs for use in configuring parts of the program.
    :rtype: dictionary
    '''

    if (directory_path):
        path = directory_path
    else:
        path = get_root_path()

    config_path = Path.joinpath(path, CONFIG_NAME)
    if (not config_path.exists()):
        raise RuntimeError("Unable to find config.json file in root!")

    config = load_json(config_path)

    ## Override the config values if the prod config file exists.
    prod_config_path = Path.joinpath(path, PROD_CONFIG_NAME)
    if (prod_config_path.exists()):
        prod_config = load_json(prod_config_path)

        for key, value in prod_config.items():
            config[key] = value

    ## Override the config values if the dev config file exists.
    dev_config_path = Path.joinpath(path, DEV_CONFIG_NAME)
    if (dev_config_path.exists()):
        dev_config = load_json(dev_config_path)

        for key, value in dev_config.items():
            config[key] = value

    return config


def load_module_config(directory_path: Path) -> dict:
    config = load_config()
    module_config = load_config(directory_path)

    ## Merge the module's configuration in, prefering it over any of the root configurations
    for key, value in module_config.items():
        config[key] = value

    return config


def is_linux():
    return ("linux" in PLATFORM)


def is_windows():
    return ("win" in PLATFORM)


def initialize_logging(logger):
    config = load_config()

    log_format = "%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    logging.basicConfig(format=log_format)

    log_level = str(config.get("log_level", "DEBUG"))
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
    log_path = config.get("log_path")
    if (log_path):
        log_path = Path(log_path)
    else:
        log_path = Path.joinpath(get_root_path(), 'logs')

    log_path.mkdir(parents=True, exist_ok=True)    # Basically a mkdir -p $log_path
    log_file_name = f"{CONFIG_OPTIONS.get('name', 'service')}.log"
    log_file = Path(log_path, log_file_name)    # Build the true path to the log file

    ## Windows has an issue with overwriting old logs (from the previous day, or older) automatically so just delete
    ## them. This is hacky, but I only use Windows for development (and don't recommend it for deployment) so it's not a
    ## big deal.
    removed_previous_logs = False
    if (is_windows() and log_file.exists()):
        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(log_file))
        now = datetime.datetime.now()
        if (last_modified.day != now.day):
            os.remove(log_file)
            removed_previous_logs = True

    ## Setup and add the timed rotating log handler to the logger
    backup_count = config.get("log_backup_count", 7)    # Store a week's logs then start overwriting them
    log_handler = TimedRotatingFileHandler(str(log_file), when='midnight', interval=1, backupCount=backup_count)
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    ## With the new logger set up, let the user know if the previously used log file was removed.
    if (removed_previous_logs):
        logger.info("Removed previous log file.")

    return logger


os.environ = {}
CONFIG_OPTIONS = load_config()
