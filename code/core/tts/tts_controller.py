import os
import asyncio
import time
import logging
from pathlib import Path

from core.exceptions import BuildingAudioFileTimedOutExeption, UnableToBuildAudioFileException
from common import utilities
from common.configuration import Configuration
from common.logging import Logging
from common.module.module import Module

import async_timeout

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class TTSController(Module):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.exe_path = TTSController.get_tts_executable_path()
        self.args = CONFIG_OPTIONS.get("args", {})
        self.audio_generate_timeout_seconds = CONFIG_OPTIONS.get("audio_generate_timeout_seconds", 3)
        self.prepend = CONFIG_OPTIONS.get("prepend", "[:phoneme on]")
        self.append = CONFIG_OPTIONS.get("append", "")
        self.char_limit = int(CONFIG_OPTIONS.get("char_limit", 1250))
        self.newline_replacement = CONFIG_OPTIONS.get("newline_replacement", "[_<250,10>]")
        self.output_extension = CONFIG_OPTIONS.get("output_extension", "wav")
        self.wine = CONFIG_OPTIONS.get("wine", "wine")
        self.xvfb_prepend = CONFIG_OPTIONS.get("xvfb_prepend", "DISPLAY=:0.0")
        self.is_headless = CONFIG_OPTIONS.get("headless", False)

        if (output_dir_path := CONFIG_OPTIONS.get("tts_output_dir_path")):
            self.output_dir_path = Path(output_dir_path)
        else:
            self.output_dir_path = Path.joinpath(utilities.get_root_path(), CONFIG_OPTIONS.get("tts_output_dir", "temp"))

        self.paths_to_delete = []

        ## Prep the output directory
        self._init_output_dir()


    def __del__(self):
        self._init_output_dir()


    @staticmethod
    def get_tts_executable_path() -> Path:
        tts_executable_path = CONFIG_OPTIONS.get("tts_executable_path")

        if (tts_executable_path is not None):
            return Path(tts_executable_path)
        else:
            return Path(utilities.get_root_path(), "code", "core", "tts", CONFIG_OPTIONS.get("tts_executable", "say.exe"))


    def _init_output_dir(self):
        if(not Path.exists(self.output_dir_path)):
            self.output_dir_path.mkdir(parents=True, exist_ok=True) # mkdir -p
        else:
            for root, dirs, files in os.walk(str(self.output_dir_path), topdown=False):
                for file in files:
                    try:
                        os.remove(os.sep.join([root, file]))
                    except OSError:
                        LOGGER.exception(f"Error removing file: {str(file)}")


    def _generate_unique_file_name(self, extension):
        time_ms = int(time.time() * 1000)
        file_name = f"{time_ms}.{extension}"

        while(os.path.isfile(file_name)):
            time_ms -= 1
            file_name = f"{time_ms}.{extension}"

        return file_name


    def check_length(self, message):
        return (len(message) <= self.char_limit)


    def _parse_message(self, message):
        if(self.newline_replacement):
            message = message.replace("\n", self.newline_replacement)

        if(self.prepend):
            message = self.prepend + message

        if(self.append):
            message = message + self.append

        message = message.replace('"', "")
        return message


    def delete(self, file_path):
        ## Basically, windows spits out a 'file in use' error when speeches are deleted after
        ## being skipped, probably because of the file being loaded into the ffmpeg player. So
        ## if the deletion fails, just pop it into a list of paths to delete on the next go around.

        if(os.path.isfile(file_path)):
            self.paths_to_delete.append(file_path)

        to_delete = []
        for path in self.paths_to_delete:
            try:
                os.remove(path)
            except FileNotFoundError:
                ## The goal was to remove the file, and as long as it doesn't exist then we're good.
                continue
            except Exception:
                LOGGER.exception(f"Error deleting file: {path}")
                to_delete.append(path)

        self.paths_to_delete = to_delete[:]

        return True


    async def save(self, message, ignore_char_limit=False):
        ## Check message size
        if(not self.check_length(message) and not ignore_char_limit):
            return None

        ## Generate and validate filename, build the output path save option, and parse the message
        output_file_path = Path.joinpath(self.output_dir_path, self._generate_unique_file_name(self.output_extension))
        save_option = f"-w \"{str(output_file_path)}\""
        message = self._parse_message(message)

        ## Build args for execution
        args = f"\"{str(self.exe_path)}\" {save_option} \"{message}\""

        ## Address issue with spaces in the path on Windows (see: https://github.com/naschorr/hawking/issues/1 and 178)
        if (utilities.is_windows()):
            args = f'\"{args}\"'

        ## Prepend the windows emulator if using linux (I'm aware of what WINE means)
        if(utilities.is_linux()):
            args = f"{self.wine} {args}"

        ## Prepend the fake display created with Xvfb if running headless
        if(self.is_headless):
            args = f"{self.xvfb_prepend} {args}"

        has_timed_out = False
        try:
            ## See https://github.com/naschorr/hawking/issues/50
            async with async_timeout.timeout(self.audio_generate_timeout_seconds):
                retval = os.system(args)
        except asyncio.TimeoutError:
            has_timed_out = True
            raise BuildingAudioFileTimedOutExeption(f"Building wav timed out for '{message}'")
        except asyncio.CancelledError as e:
            if (not has_timed_out):
                LOGGER.exception("CancelledError during wav generation, but not from a timeout!", exc_info=e)

        if(retval == 0):
            return output_file_path
        else:
            raise UnableToBuildAudioFileException(f"Couldn't build the wav file for '{message}', retval={retval}")
