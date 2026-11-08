import logging
import datetime
import os
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

from hawking.configuration import load_hawking_config
from hawking.core.services.logging.logging_config import LoggingConfig
from hawking.core.utilities.utilities import is_windows


class Logging:
    @staticmethod
    def initialize_logging(logger, logging_config: LoggingConfig | None = None):
        logging_config = logging_config or load_hawking_config().hawking.core.logging

        log_format = "%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(log_format)
        logging.basicConfig(format=log_format)

        logger.setLevel(logging_config.level.value)

        ## Get the directory containing the logs and make sure it exists, creating it if it doesn't
        log_path = logging_config.directory_path
        log_path.mkdir(parents=True, exist_ok=True)
        log_file_name = f"{logging_config.service_name}.log"
        log_file = Path(log_path, log_file_name)

        ## Windows has an issue with overwriting old logs automatically, so remove old logs.
        removed_previous_logs = False
        if is_windows() and log_file.exists():
            last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(log_file))
            now = datetime.datetime.now()
            if last_modified.day != now.day:
                os.remove(log_file)
                removed_previous_logs = True

        backup_count = logging_config.backup_count
        log_handler = TimedRotatingFileHandler(str(log_file), when='midnight', interval=1, backupCount=backup_count)
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)

        if removed_previous_logs:
            logger.info("Removed previous log file.")

        return logger