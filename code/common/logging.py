import logging
import datetime
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

from common.configuration import Configuration
from common.utilities import *


class Logging:
    @staticmethod
    def initialize_logging(logger):
        config = Configuration.load_config()

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
        log_file_name = f"{config.get('name', 'service')}.log"
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