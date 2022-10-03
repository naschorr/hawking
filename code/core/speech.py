import os
import sys
import asyncio
import time
import inspect
import logging
import random
from math import ceil
from pathlib import Path
from typing import Callable

from core.message_parser import MessageParser
from core.exceptions import MessageTooLongException, BuildingAudioFileTimedOutExeption, UnableToBuildAudioFileException
from common import utilities
from common.audio_player import AudioPlayer
from common.configuration import Configuration
from common.command_management.invoked_command import InvokedCommand
from common.command_management.invoked_command_handler import InvokedCommandHandler
from common.exceptions import WillNotConnectToVoiceChannelException
from common.logging import Logging
from common.module.module import Cog

import async_timeout
from discord import app_commands, Interaction, Member
from discord.app_commands import describe

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


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
                        LOGGER.exception("Error removing file: {}".format(file))


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
                LOGGER.exception("Error deleting file: {}".format(path))
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
        args = f'\"{str(self.exe_path)}\" {save_option} \"{message}\"'

        ## Address issue with spaces in the path on Windows (see: https://github.com/naschorr/hawking/issues/1 and 178)
        if (utilities.is_windows()):
            args = f'\"{args}\"'

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
                retval = os.system(args)
        except asyncio.TimeoutError:
            has_timed_out = True
            raise BuildingAudioFileTimedOutExeption("Building wav timed out for '{}'".format(message))
        except asyncio.CancelledError as e:
            if (not has_timed_out):
                LOGGER.exception("CancelledError during wav generation, but not from a timeout!", exc_info=e)

        if(retval == 0):
            return output_file_path
        else:
            raise UnableToBuildAudioFileException("Couldn't build the wav file for '{}', retval={}".format(message, retval))


class Speech(Cog):

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.audio_player_cog: AudioPlayer = kwargs.get('dependencies', {}).get('AudioPlayer')
        assert(self.audio_player_cog is not None)
        self.invoked_command_handler: InvokedCommandHandler = kwargs.get('dependencies', {}).get('InvokedCommandHandler')
        assert(self.invoked_command_handler is not None)
        self.message_parser: MessageParser = kwargs.get('dependencies', {}).get('MessageParser')
        assert(self.message_parser is not None)

        self.channel_timeout_phrases = CONFIG_OPTIONS.get('channel_timeout_phrases', [])
        self.audio_player_cog.channel_timeout_handler = self.play_random_channel_timeout_message
        self.tts_controller = TTSController()

    ## Methods

    async def play_random_channel_timeout_message(self, server_state, callback):
        '''Channel timeout logic, picks an appropriate sign-off message and plays it'''

        try:
            if (len(self.channel_timeout_phrases) > 0):
                message = random.choice(self.channel_timeout_phrases)
                file_path = await self.build_audio_file(message, True)

                await self.audio_player_cog._play_audio_via_server_state(server_state, file_path, callback)
        except Exception as e:
            LOGGER.exception("Exception during channel sign-off")
            await callback()


    async def build_audio_file(self, text: str, ignore_char_limit = False, interaction: Interaction = None) -> Path:
        '''Turns a string of text into a wav file for later playing. Returns a filepath pointing to that file.'''

        ## Make sure the message isn't too long
        if(not self.tts_controller.check_length(text) and not ignore_char_limit):
            raise MessageTooLongException(f"Message is {len(text)} characters long when it should be less than {self.tts_controller.char_limit}")

        ## Parse down the message before sending it to the TTS service
        if (interaction is not None):
            text = self.message_parser.parse_message(text, interaction.data)

        ## Build the audio file for speaking
        return await self.tts_controller.save(text, ignore_char_limit)


    async def say(
            self,
            text: str,
            author: Member,
            target_member: Member = None,
            ignore_char_limit = False,
            interaction: Interaction = None,
            callback: Callable = None
    ) -> InvokedCommand:
        '''Internal say method, for use with presets and anything else that generates phrases on the fly'''

        async def audio_player_callback():
            self.tts_controller.delete(wav_path)
            if (callback is None):
                return

            await callback()


        try:
            wav_path = await self.build_audio_file(text, ignore_char_limit, interaction)

        except BuildingAudioFileTimedOutExeption as e:
            LOGGER.exception(f"Timed out building audio for message: '{text}'")
            return InvokedCommand(False, e, f"Sorry, <@{author.id}>, it took too long to generate speech for that.")

        except MessageTooLongException as e:
            LOGGER.warn(f"Unable to build too long message. Message was {len(text)} characters long (out of {self.tts_controller.char_limit})")
            ## todo: Specify how many characters need to be removed?
            return InvokedCommand(False, e, f"Wow <@{author.id}>, that's waaay too much. You've gotta keep messages shorter than {self.tts_controller.char_limit} characters.")

        except UnableToBuildAudioFileException as e:
            LOGGER.exception(f"Unable to build .wav file for message: '{text}'")
            return InvokedCommand(False, e, f"Sorry, <@{author.id}>, I can't say that right now.")

        try:
            await self.audio_player_cog.play_audio(wav_path, author, target_member or author, interaction, audio_player_callback)

        except FileNotFoundError as e:
            LOGGER.exception("FileNotFound when invoking `play_audio`", e)
            return InvokedCommand(False, e, f"Sorry, <@{author.id}>, I can't say that right now.")

        except WillNotConnectToVoiceChannelException as e:
            LOGGER.exception("Cannot connect to voice channel", e)
            return InvokedCommand(False, e, f"Sorry, <@{author.id}>, I'm not able to connect to that voice channel.")

        return InvokedCommand(True)

    ## Commands

    @app_commands.command(name="say")
    @describe(text="The text that Hawking will speak")
    @describe(user="The user that will be spoken to")
    async def say_command(self, interaction: Interaction, text: str, user: Member = None):
        """Speaks your text aloud"""

        mention = self.invoked_command_handler.get_first_mention(interaction)
        invoked_command = lambda: self.say(text, interaction.user, user or mention or None, False, interaction)

        await self.invoked_command_handler.handle_deferred_command(interaction, invoked_command, ephemeral=False)
