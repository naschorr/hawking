import os
import asyncio
import time
import logging
from pathlib import Path

from hawking.modules.speech.speech_exceptions import BuildingAudioFileTimedOutExeption, UnableToBuildAudioFileException
from hawking.core.utilities import utilities
from hawking.core.services.logging.logging_service import Logging
from hawking.core.services.module_manager.module import Module
from hawking.services.tts_manager.tts_controller_config import TTSControllerConfig

import async_timeout


class TTSController(Module):
    def __init__(self, config: TTSControllerConfig, **kwargs):
        super().__init__(**kwargs)

        self.config = config
        self.logger = Logging.initialize_logging(logging.getLogger(__name__))

        self.exe_path = self.get_tts_executable_path()
        self.args = self.config.args
        self.audio_generate_timeout_seconds = self.config.generate_timeout_seconds
        self.output_extension = self.config.output_extension
        self.wine = self.config.wine_command
        self.xvfb_prepend = self.config.xvfb_prepend
        self.is_headless = self.config.headless
        self.output_dir_path = self.config.output_directory_path

        self.paths_to_delete = []

        ## Prep the output directory
        self._init_output_dir()


    def __del__(self):
        self._init_output_dir()


    def get_tts_executable_path(self) -> Path:
        return self.config.executable_path


    def _init_output_dir(self):
        if(not Path.exists(self.output_dir_path)):
            self.output_dir_path.mkdir(parents=True, exist_ok=True) # mkdir -p
        else:
            for root, dirs, files in os.walk(str(self.output_dir_path), topdown=False):
                for file in files:
                    try:
                        os.remove(os.sep.join([root, file]))
                    except OSError:
                        self.logger.exception(f"Error removing file: {str(file)}")


    def _generate_unique_file_name(self, extension):
        time_ms = int(time.time() * 1000)
        file_name = f"{time_ms}.{extension}"

        while(os.path.isfile(file_name)):
            time_ms -= 1
            file_name = f"{time_ms}.{extension}"

        return file_name


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
                self.logger.exception(f"Error deleting file: {path}")
                to_delete.append(path)

        self.paths_to_delete = to_delete[:]

        return True


    async def save(self, message):
        ## Generate filename and output path
        output_file_path = Path.joinpath(self.output_dir_path, self._generate_unique_file_name(self.output_extension))
        save_option = f"-w \"{str(output_file_path)}\""
        message = message.replace('"', "")

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
        retval = 1
        try:
            ## See https://github.com/naschorr/hawking/issues/50
            async with async_timeout.timeout(self.audio_generate_timeout_seconds):
                retval = os.system(args)
        except asyncio.TimeoutError:
            has_timed_out = True
            raise BuildingAudioFileTimedOutExeption(f"Building wav timed out for '{message}'")
        except asyncio.CancelledError as e:
            if (not has_timed_out):
                self.logger.exception("CancelledError during wav generation, but not from a timeout!", exc_info=e)

        if(retval == 0):
            return output_file_path
        else:
            raise UnableToBuildAudioFileException(f"Couldn't build the wav file for '{message}', retval={retval}")
