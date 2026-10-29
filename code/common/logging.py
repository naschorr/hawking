import logging
import datetime
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

from common.configuration.configuration import load_hawking_config
from common.logging_config import LoggingConfig
from common.utilities import *


class Logging:
    @staticmethod
    def initialize_logging(logger, logging_config: LoggingConfig | None = None):
        logging_config = logging_config or load_hawking_config().hawking.logging

        log_format = "%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(log_format)
        logging.basicConfig(format=log_format)

        logger.setLevel(logging_config.level.value)

        ## Get the directory containing the logs and make sure it exists, creating it if it doesn't
        log_path = logging_config.directory_path
        log_path.mkdir(parents=True, exist_ok=True)    # Basically a mkdir -p $log_path
        log_file_name = f"{logging_config.service_name}.log"
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
        backup_count = logging_config.backup_count    # Store a week's logs then start overwriting them
        log_handler = TimedRotatingFileHandler(str(log_file), when='midnight', interval=1, backupCount=backup_count)
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

        ## With the new logger set up, let the user know if the previously used log file was removed.
        if (removed_previous_logs):
            logger.info("Removed previous log file.")

        return logger