import logging
import random
from pathlib import Path
from typing import Callable

from core.exceptions import MessageTooLongException, BuildingAudioFileTimedOutExeption, UnableToBuildAudioFileException
from core.tts.tts_controller import TTSController
from common.audio_player import AudioPlayer
from common.configuration import Configuration
from common.command_management.invoked_command import InvokedCommand
from common.command_management.invoked_command_handler import InvokedCommandHandler
from common.exceptions import NoVoiceChannelAvailableException, UnableToConnectToVoiceChannelException
from common.logging import Logging
from common.module.module import Cog
from common.message_parser import MessageParser

from discord import app_commands, Interaction, Member
from discord.app_commands import describe
from discord.ext.commands import Bot


class SpeechCog(Cog):

    def __init__(self, config: Configuration, bot: Bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)

        self.logger = Logging.initialize_logging(logging.getLogger(__name__))
        self.bot = bot
        self.audio_player_cog: AudioPlayer = kwargs.get('dependencies', {}).get('AudioPlayer')
        assert(self.audio_player_cog is not None)
        self.invoked_command_handler: InvokedCommandHandler = kwargs.get('dependencies', {}).get('InvokedCommandHandler')
        assert(self.invoked_command_handler is not None)
        self.message_parser: MessageParser = kwargs.get('dependencies', {}).get('MessageParser')
        assert(self.message_parser is not None)
        self.tts_controller: TTSController = kwargs.get('dependencies', {}).get('TTSController')
        assert(self.tts_controller is not None)

        self.channel_timeout_phrases = config.get('channel_timeout_phrases', [])
        self.audio_player_cog.channel_timeout_handler = self.play_random_channel_timeout_message

        ## Commands
        self.add_command(app_commands.Command(
            name="say",
            description=self.say_command.__doc__ or "Says your text aloud",
            callback=self.say_command
        ))

    ## Methods

    async def play_random_channel_timeout_message(self, server_state, callback):
        '''Channel timeout logic, picks an appropriate sign-off message and plays it'''

        try:
            if (len(self.channel_timeout_phrases) > 0):
                message = random.choice(self.channel_timeout_phrases)
                file_path = await self.build_audio_file(message, True)

                await self.audio_player_cog._play_audio_via_server_state(server_state, file_path, callback)
        except Exception as e:
            self.logger.exception("Exception during channel sign-off")
            await callback()


    async def build_audio_file(
            self,
            text: str,
            ignore_char_limit = False,
            interaction: Interaction | None = None
    ) -> Path:
        '''Turns a string of text into a wav file for later playing. Returns a filepath pointing to that file.'''

        ## Make sure the message isn't too long
        if(not self.tts_controller.check_length(text) and not ignore_char_limit):
            raise MessageTooLongException(f"Message is {len(text)} characters long when it should be less than {self.tts_controller.char_limit}")

        ## Parse down the message before sending it to the TTS service
        if (interaction is not None and interaction.data is not None):
            text = self.message_parser.parse_message(text, interaction.data)

        ## Build the audio file for speaking
        file_path = await self.tts_controller.save(text, ignore_char_limit)
        
        if (file_path is None):
            raise UnableToBuildAudioFileException(f"Unable to save audio file for message: '{text}'")
        else:
            return file_path


    async def say(
            self,
            *,
            text: str,
            author: Member,
            ignore_char_limit: bool = False,
            target_member: Member | None = None,
            interaction: Interaction | None = None,
            callback: Callable | None = None
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
            self.logger.exception(f"Timed out building audio for message: '{text}'")
            return InvokedCommand(False, e, f"Sorry <@{author.id}>, it took too long to generate speech for that.")

        except MessageTooLongException as e:
            self.logger.warn(f"Unable to build too long message. Message was {len(text)} characters long (out of {self.tts_controller.char_limit})")
            ## todo: Specify how many characters need to be removed?
            return InvokedCommand(False, e, f"Wow <@{author.id}>, that's waaay too much. You've gotta keep messages shorter than {self.tts_controller.char_limit} characters.")

        except UnableToBuildAudioFileException as e:
            self.logger.exception(f"Unable to build .wav file for message: '{text}'")
            return InvokedCommand(False, e, f"Sorry <@{author.id}>, I can't say that right now.")

        try:
            await self.audio_player_cog.play_audio(
                file_path=wav_path,
                author=author,
                target_member=target_member or author,
                interaction=interaction,
                callback=audio_player_callback
            )

        except NoVoiceChannelAvailableException as e:
            self.logger.error("No voice channel available", exc_info=e)
            if (e.target_member.id == author.id):
                return InvokedCommand(False, e, f"Sorry <@{author.id}>, you're not in a voice channel.")
            else:
                return InvokedCommand(False, e, f"Sorry <@{author.id}>, that person isn't in a voice channel.")

        except UnableToConnectToVoiceChannelException as e:
            ## Logging handled in AudioPlayer

            error_values = []
            if (not e.can_connect):
                error_values.append("connect to")
            if (not e.can_speak):
                error_values.append("speak in")

            return InvokedCommand(False, e, f"Sorry <@{author.id}>, I'm not able to {' or '.join(error_values)} that channel. Check the permissions and try again later.")

        except FileNotFoundError as e:
            self.logger.error("FileNotFound when invoking `play_audio`", exc_info=e)
            return InvokedCommand(False, e, f"Sorry <@{author.id}>, I can't say that right now.")

        return InvokedCommand(True)

    ## Commands

    @describe(text="The text that Hawking will speak")
    @describe(user="The user that will be spoken to")
    async def say_command(self, interaction: Interaction, text: str, user: Member | None = None):
        """Speaks your text aloud"""

        ## Make sure the author is a member, and not just a user (kind of a frustrating disctinction for this use case,
        ## but keeping the type checker happy is worth it)
        author = None
        if (isinstance(interaction.user, Member)):
            author = interaction.user
        else:
            self.logger.debug(f"Author '{interaction.user.id}' is not of type Member, say_command will be skipped.")
            return

        ## Build the command and invoke it
        async def invokable_command() -> InvokedCommand:
            return await self.say(
                text=text,
                author=author,
                target_member=user or self.invoked_command_handler.get_first_mention(interaction) or None,
                ignore_char_limit=False,
                interaction=interaction
            )
        await self.invoked_command_handler.invoke_command(interaction, invokable_command, ephemeral=False)
