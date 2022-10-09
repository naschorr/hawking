import os
import sys
import asyncio
import async_timeout
import time
import inspect
import logging
import random
import math
from typing import Callable
from concurrent import futures
from pathlib import Path

from common import utilities
from common.configuration import Configuration
from common.exceptions import UnableToConnectToVoiceChannelException, NoVoiceChannelAvailableException
from common.logging import Logging
from common.database.database_manager import DatabaseManager
from common.module.module import Cog

import discord
from discord.ext import commands
from discord import app_commands, Interaction, Guild, Member, VoiceClient, VoiceChannel, FFmpegPCMAudio

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class AudioPlayRequest:
    '''
    Represents a user's request for the bot to play some audio.
    Instances of this class form the 'audio_play_queue' in a ServerStateManager instance.
    '''

    def __init__(
        self,
        author: Member | None,
        target: Member | None,
        channel: VoiceChannel,
        audio: FFmpegPCMAudio,
        file_path: Path,
        interaction: Interaction = None,
        callback: Callable = None
    ):
        self.author = author
        self.target = target
        self.channel = channel
        self.audio = audio
        self.file_path = file_path
        self.interaction = interaction
        self.callback = callback
        self.skipped = False


    def __str__(self):
        return f"'{self.author.name if self.author else 'No Author'}' in '{self.channel.name}' wants '{self.file_path}'"


class ServerStateManager:
    '''
    Manages the state of the bot in a given server.
    This class helps to manage the bot, initiate audio play requests, and move between channels.
    '''

    def __init__(self, bot: commands.Bot, audio_player_cog, guild: Guild, channel_timeout_handler = None):
        self.bot = bot
        self.audio_player_cog = audio_player_cog
        self.guild = guild
        self.active_play_request: AudioPlayRequest = None
        self.next = asyncio.Event() # flag for alerting the audio_player to play the next AudioPlayRequest
        self.skip_votes = set() # set of Members that voted to skip
        self.audio_play_queue = asyncio.Queue() # queue of AudioPlayRequest to play
        self.audio_player = self.bot.loop.create_task(self.audio_player_loop())
        self.voice_client = None

        self.channel_timeout_seconds = int(CONFIG_OPTIONS.get('channel_timeout_seconds', 15 * 60))
        self.channel_timeout_handler = channel_timeout_handler

    ## Property(s)

    @property
    def audio(self) -> discord.FFmpegPCMAudio:
        return self.active_play_request.audio


    @property
    def channel(self) -> discord.VoiceChannel:
        return self.active_play_request.channel


    @property
    def interaction(self) -> Interaction:
        if (self.active_play_request is None):
            return None


    @property
    def voice_client(self) -> VoiceClient | None:
        return self._voice_client


    @voice_client.setter
    def voice_client(self, value: VoiceClient | None):
        self._voice_client = value


    @property
    def is_playing(self) -> bool:
        '''Is this ServerStateManager currently playing audio?'''

        if(self.voice_client is None):
            return False

        return self.voice_client.is_playing()

    ## Methods

    async def get_members(self, include_bots = False) -> list[Member]:
        '''Returns a set of members in the current voice channel'''

        members = self.active_play_request.channel.members

        if (include_bots):
            return members
        else:
            return [member for member in members if member.bot == False]


    async def add_play_request(self, play_request: AudioPlayRequest):
        '''Pushes the given play_request into the audio_play_queue'''

        await self.audio_play_queue.put(play_request)


    async def get_voice_client(self, channel: discord.VoiceChannel) -> VoiceClient:
        '''Handles voice client management by connecting, and moving between voice channels'''

        me = self.guild.get_member(self.bot.user.id)
        permissions: discord.Permissions = channel.permissions_for(me)

        if (not permissions.connect or not permissions.speak):
            raise UnableToConnectToVoiceChannelException(
                "Unable to speak and/or connect to the channel",
                channel,
                can_speak=permissions.speak,
                can_connect=permissions.connect
            )

        if (self.voice_client is not None):
            ## Check to see if the bot isn't already in the correct channel
            if (self.voice_client.channel.id != channel.id):
                await self.voice_client.move_to(channel)

            return self.voice_client

        return await channel.connect()


    def skip_audio(self):
        '''Skips the currently playing audio. If more audio is queued up, it will be played immediately.'''

        if(self.is_playing):
            LOGGER.debug(
                f"Skipping file at: {self.active_play_request.file_path}, "
                f"in channel: {self.voice_client.channel.name}, "
                f"in server: {self.guild.name}, "
                f"for user: {self.active_play_request.author.name if self.active_play_request.author else None}"
            )
            self.voice_client.stop()

        self.active_play_request.skipped = True
        self.next.set()
        self.skip_votes.clear()


    async def disconnect(self, inactive=False):
        """Disconnects the current voice client from the current channel"""

        async def clean_up_voice_client():
            await self.voice_client.disconnect()
            LOGGER.debug(f"Successfully disconnected voice client from channel: {self.voice_client.channel.name}, in server: {self.guild.name}")
            self.voice_client = None


        ## No voice client to disconnect!
        if (self.voice_client is None):
            return

        ## Try to use the channel_timeout_handler, if this a disconnect that the bot initiated due to inactivity.
        if (inactive and self.channel_timeout_handler):
            LOGGER.debug(
                f"Attempting to leave channel: {self.voice_client.channel.name}, "
                f"in server: {self.guild.name}, "
                f"due to inactivity for past {self.channel_timeout_seconds} seconds"
            )

            ## Note that this doesn't actually wait for the speech process to continue.
            await self.channel_timeout_handler(self, clean_up_voice_client)
        else:
            LOGGER.debug(f"Attempting to leave channel: {self.voice_client.channel.name}, in server: {self.guild.name}")
            await clean_up_voice_client()


    async def audio_player_loop(self):
        '''
        Audio player event loop task.
        This event loop handles processing the play_queue by joining the requester's channel, playing the requested
        audio, and handling successful skip requests
        '''

        while(True):
            try:
                self.next.clear()
                self.active_play_request = None

                try:
                    async with async_timeout.timeout(self.channel_timeout_seconds):
                        self.active_play_request: AudioPlayRequest = await self.audio_play_queue.get()
                        LOGGER.debug(f"Got new audio play request: {self.active_play_request}")
                except asyncio.TimeoutError:
                    if (self.voice_client and self.voice_client.is_connected()):
                        self.bot.loop.create_task(self.disconnect(inactive=True))
                    continue
                except asyncio.CancelledError as e:
                    LOGGER.exception("CancelledError during audio_player_loop, ignoring and continuing loop.", e)
                    continue

                ## Join the requester's voice channel & play their requested audio (Or Handle the appropriate exception)
                try:
                    self.voice_client = await self.get_voice_client(self.active_play_request.channel)
                except futures.TimeoutError:
                    LOGGER.error("Timed out trying to connect to the voice channel")
                    if (self.active_play_request.interaction is not None and self.active_play_request.interaction.followup is not None):
                        await self.active_play_request.interaction.followup.send(
                            f"Sorry <@{self.active_play_request.author.id}>, I can't connect to that channel right now."
                        )
                    continue

                except UnableToConnectToVoiceChannelException as e:
                    LOGGER.error("Unable to connect to voice channel")

                    required_permission_phrases = []
                    if (not e.can_connect):
                        required_permission_phrases.append("connect to that channel")
                    if (not e.can_speak):
                        required_permission_phrases.append("speak in that channel")

                    if (self.active_play_request.interaction is not None and self.active_play_request.interaction.followup is not None):
                        await self.active_play_request.interaction.followup.send(
                            f"Sorry <@{self.active_play_request.author.id}>, I don't have permission to {' or '.join(required_permission_phrases)}"
                        )
                    continue

                if (self.is_playing):
                    self.voice_client.stop()

                def after_play_callback_builder():
                    ## Wrap this in a closure to keep it available even when it should be out of scope
                    current_active_play_request = self.active_play_request

                    def after_play(_):
                        self.skip_votes.clear()

                        if (id(self.active_play_request) == id(current_active_play_request)):
                            self.next.set()

                            ## Perform callback after the audio has finished (assuming it's defined)
                            callback = current_active_play_request.callback
                            if(callback):
                                if(asyncio.iscoroutinefunction(callback)):
                                    self.bot.loop.create_task(callback())
                                else:
                                    callback()

                    return after_play

                LOGGER.debug(
                    f"Playing file at: {self.active_play_request.file_path}, "
                    f"in channel: {self.active_play_request.channel.name}, "
                    f"in server: {self.active_play_request.channel.guild.name}, "
                    f"for user: {self.active_play_request.author.name if self.active_play_request.author else None}"
                )
                self.voice_client.play(self.active_play_request.audio, after=after_play_callback_builder())
                await self.next.wait()

            except Exception as e:
                LOGGER.exception('Exception inside audio player event loop', e)


class AudioPlayer(Cog):
    ## Keys
    SKIP_PERCENTAGE_KEY = "skip_percentage"
    FFMPEG_PARAMETERS_KEY = "ffmpeg_parameters"
    FFMPEG_POST_PARAMETERS_KEY = "ffmpeg_post_parameters"


    def __init__(self, bot: commands.Bot, channel_timeout_handler = None, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)

        self.bot = bot
        self.admin_cog = kwargs.get('dependencies', {}).get('AdminCog')
        assert (self.admin_cog is not None)
        self.database_manager: DatabaseManager = kwargs.get('dependencies', {}).get('DatabaseManager')
        assert (self.database_manager is not None)

        self.server_states = {}
        self.channel_timeout_handler = channel_timeout_handler

        ## Clamp between 0.0 and 1.0
        self.skip_percentage = max(min(float(CONFIG_OPTIONS.get(self.SKIP_PERCENTAGE_KEY, 0.5)), 1.0), 0.0)
        self.ffmpeg_parameters = CONFIG_OPTIONS.get(self.FFMPEG_PARAMETERS_KEY, "")
        self.ffmpeg_post_parameters = CONFIG_OPTIONS.get(self.FFMPEG_POST_PARAMETERS_KEY, "")

        ## Commands
        self.add_command(app_commands.Command(
            name="skip",
            description=self.skip_command.__doc__,
            callback=self.skip_command
        ))

        ## Admin Commands
        @self.admin_cog.admin.command()
        async def skip(ctx):
            """Skips the current audio"""

            await self.database_manager.store(ctx)

            await self.skip(ctx, force = True)


        @self.admin_cog.admin.command()
        async def disconnect(ctx):
            """Disconnect from the current voice channel"""

            await self.database_manager.store(ctx)

            state = self.get_server_state(ctx)
            await state.disconnect()

    ## Properties

    @property
    def channel_timeout_handler(self):
        return self._channel_timeout_handler


    @channel_timeout_handler.setter
    def channel_timeout_handler(self, handler):
        self._channel_timeout_handler = handler

        for server_state in self.server_states.values():
            server_state.channel_timeout_handler = self.channel_timeout_handler

    ## Methods

    ## This isn't ideal, but in Python 3.6 we can't use the assignment operator in a lambda, so this manual setter has
    ## to go in it's place.
    ## todo: look into this
    def set_channel_timeout_handler(self, handler):
        self.channel_timeout_handler = handler


    def get_server_state(self, guild: Guild) -> ServerStateManager:
        '''Retrieves the server state for the provided guild, or creates a new one if no others exist'''

        server_state = self.server_states.get(guild.id)

        if (server_state is None):
            server_state = ServerStateManager(self.bot, self, guild, self.channel_timeout_handler)
            self.server_states[guild.id] = server_state

        return server_state


    def build_player(self, file_path: Path) -> discord.FFmpegPCMAudio:
        '''Builds an audio player for playing the file located at 'file_path'.'''

        return discord.FFmpegPCMAudio(
            str(file_path),
            before_options=self.ffmpeg_parameters,
            options=self.ffmpeg_post_parameters
        )


    async def play_audio(self, file_path: Path, author: Member, target_member: Member, interaction: Interaction = None, callback: Callable = None):
        '''Plays the given audio file aloud to your channel'''

        ## Make sure file_path points to an actual file
        if (not file_path.is_file()):
            error_text = f"Unable to play file at: {file_path}, file doesn't exist or isn't a file."
            LOGGER.error(error_text)
            raise FileNotFoundError(error_text)

        ## Verify that the target/requester is in a channel
        voice_channel = None
        if (target_member.voice is None):
            error_text = f"Target member {target_member.id} isn't in a voice channel"
            LOGGER.warn(error_text)
            raise NoVoiceChannelAvailableException(error_text, target_member)
        voice_channel = target_member.voice.channel

        ## Get/Build a state for this audio, build the player, and add it to the state
        state = self.get_server_state(target_member.guild)
        player = self.build_player(file_path)
        await state.add_play_request(AudioPlayRequest(author, target_member, voice_channel, player, file_path, interaction, callback))



    async def _play_audio_via_server_state(self, server_state: ServerStateManager, file_path: Path, callback: Callable = None):
        '''Internal method for playing audio without a requester. Instead it'll play from the active voice_client.'''

        ## Make sure file_path points to an actual file
        if (not file_path.is_file()):
            error_text = f"Unable to play file at: {file_path}, file doesn't exist or isn't a file."
            LOGGER.error(error_text)
            raise FileNotFoundError(error_text)

        ## Create a player for the audio file
        player = self.build_player(file_path)

        ## On successful player creation, build a AudioPlayRequest and push it into the queue
        play_request = AudioPlayRequest(None, None, server_state.voice_client.channel, player, file_path, None, callback)
        await server_state.add_play_request(play_request)

    ## Commands

    async def skip_command(self, interaction: Interaction):
        '''Vote to skip what's currently playing'''

        state = self.get_server_state(interaction.guild)

        ## Is the bot speaking?
        if(not state.is_playing):
            await self.database_manager.store(interaction, valid=False)
            await interaction.response.send_message("I'm not speaking at the moment.", ephemeral=True)

        ## Add a skip vote and tally it up!
        voter = interaction.user
        if(voter == state.active_play_request.author):
            state.skip_audio()
            await self.database_manager.store(interaction)
            await interaction.response.send_message(f"<@{voter.id}> skipped their own audio.")

        elif(voter.id not in state.skip_votes):
            state.skip_votes.add(voter.id)

            ## Ensure all voters are still in the current channel (no drive-by skipping)
            active_members = await state.get_members()
            active_voters = [voter for voter in state.skip_votes if any(voter.id == member.id for member in active_members)]
            total_votes = len(active_voters)

            ## Determine if a skip should happen or not
            vote_percentage = total_votes / len(active_members)
            if(vote_percentage >= self.skip_percentage):
                state.skip_audio()
                await self.database_manager.store(interaction)
                await interaction.response.send_message("Skip vote passed!")

            else:
                ## The total votes needed for a successful skip
                required_votes = math.ceil(len(active_members) * self.skip_percentage)

                await self.database_manager.store(interaction)
                await interaction.response.send_message(f"Skip vote added! Currently at {total_votes} of {required_votes} votes.")

        else:
            await self.database_manager.store(interaction, valid=False)
            await interaction.response.send_message(f"<@{voter.id}> has already voted!", ephemeral=True)
