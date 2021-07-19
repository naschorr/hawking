import os
import sys
import asyncio
import time
import inspect
import logging
import random
from math import ceil
from pathlib import Path

from core import message_parser
from core.exceptions import MessageTooLongException, BuildingAudioFileTimedOutExeption, UnableToBuildAudioFileException
from common import utilities
from common.module.discoverable_module import DiscoverableCog

import async_timeout
from aioify import aioify
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class TTSController:
    ## Keys
    ARGS_KEY = "args"
    PREPEND_KEY = "prepend"
    APPEND_KEY = "append"
    CHAR_LIMIT_KEY = "char_limit"
    NEWLINE_REPLACEMENT_KEY = "newline_replacement"
    OUTPUT_EXTENSION_KEY = "output_extension"
    WINE_KEY = "wine"
    XVFB_PREPEND_KEY = "XVFB_prepend"
    HEADLESS_KEY = "headless"

    ## Defaults
    PREPEND = CONFIG_OPTIONS.get(PREPEND_KEY, "[:phoneme on]")
    APPEND = CONFIG_OPTIONS.get(APPEND_KEY, "")
    CHAR_LIMIT = CONFIG_OPTIONS.get(CHAR_LIMIT_KEY, 1250)
    NEWLINE_REPLACEMENT = CONFIG_OPTIONS.get(NEWLINE_REPLACEMENT_KEY, "[_<250,10>]")
    OUTPUT_EXTENSION = CONFIG_OPTIONS.get(OUTPUT_EXTENSION_KEY, "wav")
    WINE = CONFIG_OPTIONS.get(WINE_KEY, "wine")
    XVFB_PREPEND = CONFIG_OPTIONS.get(XVFB_PREPEND_KEY, "DISPLAY=:0.0")
    HEADLESS = CONFIG_OPTIONS.get(HEADLESS_KEY, False)


    def __init__(self, **kwargs):
        self.exe_path = TTSController.get_tts_executable_path()
        self.args = kwargs.get(self.ARGS_KEY, {})
        self.audio_generate_timeout_seconds = CONFIG_OPTIONS.get("audio_generate_timeout_seconds", 3)
        self.prepend = kwargs.get(self.PREPEND_KEY, self.PREPEND)
        self.append = kwargs.get(self.APPEND_KEY, self.APPEND)
        self.char_limit = int(kwargs.get(self.CHAR_LIMIT_KEY, self.CHAR_LIMIT))
        self.newline_replacement = kwargs.get(self.NEWLINE_REPLACEMENT_KEY, self.NEWLINE_REPLACEMENT)
        self.output_extension = kwargs.get(self.OUTPUT_EXTENSION_KEY, self.OUTPUT_EXTENSION)
        self.wine = kwargs.get(self.WINE_KEY, self.WINE)
        self.xvfb_prepend = kwargs.get(self.XVFB_PREPEND_KEY, self.XVFB_PREPEND)
        self.is_headless = kwargs.get(self.HEADLESS_KEY, self.HEADLESS)

        output_dir_path = CONFIG_OPTIONS.get('tts_output_dir_path')
        if (output_dir_path):
            self.output_dir_path = Path(output_dir_path)
        else:
            self.output_dir_path = Path.joinpath(utilities.get_root_path(), CONFIG_OPTIONS.get('tts_output_dir', 'temp'))

        self.paths_to_delete = []
        self.async_os = aioify(obj=os, name='async_os')

        ## Prep the output directory
        self._init_output_dir()


    def __del__(self):
        self._init_output_dir()


    @staticmethod
    def get_tts_executable_path() -> Path:
        tts_executable_path = CONFIG_OPTIONS.get('tts_executable_path')

        if (tts_executable_path is not None):
            return Path(tts_executable_path)
        else:
            return Path(utilities.get_root_path(), 'code', 'core', 'tts', CONFIG_OPTIONS.get('tts_executable', 'say.exe'))


    @staticmethod
    def set_current_working_dir_to_tts_executable():
        '''
        Conveniently ensures that the current working directory is set to the location of the tts executable. This is
        ESSENTIAL for the tts executable to work properly.
        '''

        exe_path = TTSController.get_tts_executable_path()

        if (exe_path.parent != Path(os.getcwd())):
            os.chdir(exe_path.parent)


    def _init_output_dir(self):
        if(not Path.exists(self.output_dir_path)):
            self.output_dir_path.mkdir(parents=True, exist_ok=True) # mkdir -p
        else:
            for root, dirs, files in os.walk(str(self.output_dir_path), topdown=False):
                for file in files:
                    try:
                        os.remove(os.sep.join([root, file]))
                    except OSError:
                        logger.exception("Error removing file: {}".format(file))


    def _generate_unique_file_name(self, extension):
        time_ms = int(time.time() * 1000)
        file_name = "{}.{}".format(time_ms, extension)

        while(os.path.isfile(file_name)):
            time_ms -= 1
            file_name = "{}.{}".format(time_ms, extension)

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
                logger.exception("Error deleting file: {}".format(path))
                to_delete.append(path)

        self.paths_to_delete = to_delete[:]

        return True


    async def save(self, message, ignore_char_limit=False):
        ## Check message size
        if(not self.check_length(message) and not ignore_char_limit):
            return None

        ## Generate and validate filename, build the output path save option, and parse the message
        output_file_path = Path.joinpath(self.output_dir_path, self._generate_unique_file_name(self.output_extension))
        save_option = '-w "{}"'.format(str(output_file_path))
        message = self._parse_message(message)

        ## Build args for execution
        ## The quotes fix an issue with spaces in the path, see: https://github.com/naschorr/hawking/issues/1
        args = '\"\"{}\" {} \"{}\"\"'.format(
            str(self.exe_path),
            save_option,
            message
        )

        ## Prepend the windows emulator if using linux (I'm aware of what WINE means)
        if(utilities.is_linux()):
            args = "{} {}".format(self.wine, args)

        ## Prepend the fake display created with Xvfb if running headless
        if(self.is_headless):
            args = "{} {}".format(self.xvfb_prepend, args)

        has_timed_out = False
        try:
            ## See https://github.com/naschorr/hawking/issues/50
            async with async_timeout.timeout(self.audio_generate_timeout_seconds):
                retval = await self.async_os.system(command=args)
        except asyncio.TimeoutError:
            has_timed_out = True
            raise BuildingAudioFileTimedOutExeption("Building wav timed out for '{}'".format(message))
        except asyncio.CancelledError as e:
            if (not has_timed_out):
                logger.exception("CancelledError during wav generation, but not from a timeout!", exc_info=e)

        if(retval == 0):
            return output_file_path
        else:
            raise UnableToBuildAudioFileException("Couldn't build the wav file for '{}', retval={}".format(message, retval))


class Speech(DiscoverableCog):

    def __init__(self, hawking, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hawking = hawking

        self.channel_timeout_phrases = CONFIG_OPTIONS.get('channel_timeout_phrases', [])
        self.tts_controller = TTSController()
        self.message_parser = message_parser.MessageParser()

    ## Properties

    @property
    def audio_player_cog(self):
        return self.hawking.get_audio_player_cog()

    ## Methods

    async def play_random_channel_timeout_message(self, server_state, callback):
        '''Channel timeout logic, picks an appropriate sign-off message and plays it'''

        try:
            if (len(self.channel_timeout_phrases) > 0):
                message = random.choice(self.channel_timeout_phrases)
                file_path = await self.build_audio_file(None, message, True)

                await self.audio_player_cog._play_audio_via_server_state(server_state, file_path, callback)
        except Exception as e:
            logger.exception("Exception during channel sign-off")
            await callback()


    async def build_audio_file(self, ctx, message, ignore_char_limit = False) -> str:
        '''Turns a string of text into a wav file for later playing. Returns a filepath pointing to that file.'''

        ## Make sure the message isn't too long
        if(not self.tts_controller.check_length(message) and not ignore_char_limit):
            raise MessageTooLongException(
                "Message is {} characters long when it should be less than {}".format(
                    len(message),
                    self.tts_controller.char_limit
                )
            )

        ## Parse down the message before sending it to the TTS service
        if (ctx):
            message = self.message_parser.parse_message(message, ctx.message)

        ## Build the audio file for speaking
        return await self.tts_controller.save(message, ignore_char_limit)


    async def _say(self, ctx, message, target_member = None, ignore_char_limit = False):
        '''Internal say method, for use with presets and anything else that generates phrases on the fly'''

        try:
            wav_path = await self.build_audio_file(ctx, message, ignore_char_limit)
        except BuildingAudioFileTimedOutExeption as e:
            logger.exception("Timed out building audio for message: '{}'".format(message))
            await ctx.send("Sorry, <@{}>, it took too long to generate speech for that.".format(ctx.message.author.id))
            return
        except MessageTooLongException as e:
            logger.warn("Unable to build too long message. Message was {} characters long (out of {})".format(
                len(message),
                self.tts_controller.char_limit
            ))
            await ctx.send("Wow <@{}>, that's waaay too much. You've gotta keep messages shorter than {} characters.".format(
                ctx.message.author.id,
                self.tts_controller.char_limit
            ))
            return False
        except UnableToBuildAudioFileException as e:
            logger.exception("Unable to build .wav file for message: '{}'".format(message))
            await ctx.send("Sorry, <@{}>, I can't say that right now.".format(ctx.message.author.id))
            return False

        await self.audio_player_cog.play_audio(ctx, wav_path, target_member, lambda: self.tts_controller.delete(wav_path))
        return True

    ## Commands

    @commands.command(no_pm=True)
    async def say(self, ctx, *, message, target_member = None, ignore_char_limit = False):
        '''Speaks your text aloud to your current voice channel.'''

        await self._say(ctx, message, target_member, ignore_char_limit)
