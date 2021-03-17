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

import utilities
import dynamo_manager
import exceptions
from discoverable_module import DiscoverableCog
from module_initialization_struct import ModuleInitializationStruct

import discord
from discord import errors
from discord.ext import commands
from discord.member import Member

## Config & logging
CONFIG_OPTIONS = utilities.load_config()
logger = utilities.initialize_logging(logging.getLogger(__name__))


class AudioPlayRequest:
    '''
    Represents a user's request for the bot to play some audio.
    Instances of this class form the 'audio_play_queue' in a ServerStateManager instance.
    '''

    def __init__(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel,
        audio: discord.FFmpegPCMAudio,
        file_path: Path,
        callback: Callable = None
    ):
        self.member = member
        self.channel = channel
        self.audio = audio
        self.file_path = file_path
        self.callback = callback
        self.skipped = False


    def __str__(self):
        return "'{}' in '{}' wants '{}'".format(self.member.name, self.channel.name, self.file_path)


class ServerStateManager:
    '''
    Manages the state of the bot in a given server.
    This class helps to manage the bot, initiate audio play requests, and move between channels.
    '''

    def __init__(self, ctx, bot: commands.Bot, audio_player_cog, channel_timeout_handler = None):
        self.ctx = ctx
        self.bot = bot
        self.audio_player_cog = audio_player_cog
        self.active_play_request: AudioPlayRequest = None
        self.next = asyncio.Event() # flag for alerting the audio_player to play the next AudioPlayRequest
        self.skip_votes = set() # set of Members that voted to skip
        self.audio_play_queue = asyncio.Queue() # queue of AudioPlayRequest to play
        self.audio_player = self.bot.loop.create_task(self.audio_player_loop())

        self.channel_timeout_seconds = int(CONFIG_OPTIONS.get('channel_timeout_seconds', 15 * 60))
        self.channel_timeout_handler = channel_timeout_handler

    ## Property(s)

    @property
    def audio(self) -> discord.FFmpegPCMAudio:
        return self.active_play_request.audio


    @property
    def channel(self) -> discord.VoiceChannel:
        return self.active_play_request.channel

    ## Methods

    async def get_members(self, include_bots = False) -> list:
        '''Returns a set of members in the current voice channel'''

        members = self.active_play_request.channel.members

        if (include_bots):
            return members
        else:
            return [member for member in members if member.bot == False]


    def is_playing(self) -> bool:
        '''Returns a bool to determine if the bot is speaking in this state.'''

        if(self.ctx.voice_client is None):
            return False

        return self.ctx.voice_client.is_playing()


    async def add_play_request(self, play_request: AudioPlayRequest):
        '''Pushes the given play_request into the audio_play_queue'''

        await self.audio_play_queue.put(play_request)


    async def get_voice_client(self, channel: discord.VoiceChannel):
        '''Handles voice client management by connecting, and moving between voice channels'''

        ## Make sure the bot can actually connect to the requested VoiceChannel
        permissions = channel.guild.me.permissions_in(channel)
        if (not permissions.connect or not permissions.speak):
            raise exceptions.UnableToConnectToVoiceChannelException(
                "Unable to speak and/or connect to the channel",
                channel,
                can_speak=permissions.speak,
                can_connect=permissions.connect
            )

        if (self.ctx.voice_client is not None):
            ## Check to see if the bot isn't already in the correct channel
            if (self.ctx.voice_client.channel.id != channel.id):
                await self.ctx.voice_client.move_to(channel)

            return self.ctx.voice_client
        else:
            ## NOTE: There's an issue where if you reset the app, while the bot is connected to a voice channel, upon the 
            ## bot reconnecting and joining the same voice channel, playing audio won't work.
            ## See: https://github.com/Rapptz/discord.py/issues/2284
            already_in_channel = next(filter(lambda member: member.id == self.bot.user.id, channel.members), None)
            if (already_in_channel):
                raise exceptions.AlreadyInVoiceChannelException(
                    "Old instance of bot already exists in the channel",
                    channel
                )

        return await channel.connect()


    def skip_audio(self):
        '''Skips the currently playing audio. If more audio is queued up, it will be played immediately.'''

        if(self.is_playing()):
            logger.debug("Skipping file at: {}, in channel: {}, in server: {}, for user: {}".format(
                self.active_play_request.file_path,
                self.ctx.voice_client.channel.name,
                self.ctx.guild.name,
                self.active_play_request.member.name if self.active_play_request.member else None
            ))

            self.ctx.voice_client.stop()

        self.active_play_request.skipped = True
        self.next.set()
        self.skip_votes.clear()


    async def disconnect(self, inactive=False):
        ## No voice client to disconnect!
        if (not self.ctx.voice_client):
            return

        ## Try to use the channel_timeout_handler, if this a disconnect that the bot initiated due to inactivity.
        if (inactive and self.channel_timeout_handler):
            logger.debug("Attempting to leave channel: {}, in server: {}, due to inactivity for past {} seconds".format(
                self.ctx.voice_client.channel.name,
                self.ctx.guild.name,
                self.channel_timeout_seconds
            ))  

            await self.channel_timeout_handler(self, self.ctx.voice_client.disconnect)
        else:
            logger.debug("Attempting to leave channel: {}, in server: {}".format(
                self.ctx.voice_client.channel.name,
                self.ctx.guild.name
            ))

            ## Otherwise just default to a normal voice_client disconnect
            await self.ctx.voice_client.disconnect()

        logger.debug("Successfully disconnected voice client from channel: {}, in server: {}".format(
            self.ctx.voice_client.channel.name,
            self.ctx.guild.name,
        ))


    async def audio_player_loop(self):
        '''
        Audio player event loop task.
        This event loop handles processing the play_queue by joining the requester's channel, playing the requested 
        audio, and handling successful skip requests
        '''

        while(True):
            try:
                self.next.clear()
                active_play_request = None

                try:
                    async with async_timeout.timeout(self.channel_timeout_seconds):
                        self.active_play_request = await self.audio_play_queue.get()
                        active_play_request = self.active_play_request
                except asyncio.TimeoutError:
                    if (self.ctx.voice_client and self.ctx.voice_client.is_connected()):
                        self.bot.loop.create_task(self.disconnect(inactive=True))
                    continue
                except asyncio.CancelledError:
                    logger.exception("CancelledError during audio_player_loop, ignoring and continuing loop.")
                    continue

                ## Join the requester's voice channel & play their requested audio (Or Handle the appropriate exception)
                voice_client = None
                try:
                    voice_client = await self.get_voice_client(self.active_play_request.channel)
                except futures.TimeoutError:
                    logger.error("Timed out trying to connect to the voice channel")

                    await self.ctx.send("Sorry <@{}>, I can't connect to that channel right now.".format(active_play_request.member.id))
                    continue

                except exceptions.UnableToConnectToVoiceChannelException as e:
                    logger.error("Unable to connect to voice channel")

                    required_permission_phrases = []
                    if (not e.can_connect):
                        required_permission_phrases.append("connect to that channel")
                    if (not e.can_speak):
                        required_permission_phrases.append("speak in that channel")

                    await self.ctx.send("Sorry <@{}>, I don't have permission to {}.".format(
                        self.ctx.message.author.id,
                        " or ".join(required_permission_phrases)
                    ))
                    continue

                except exceptions.AlreadyInVoiceChannelException as e:
                    logger.error("Unable to connect to voice channel, old instance of the bot already exists")

                    await self.ctx.send(
                        "Uh oh <@{}>, looks like I'm still in the channel! Wait until I disconnect before trying again."
                        .format(self.ctx.message.author.id)
                    )
                    continue

                if (voice_client.is_playing()):
                    voice_client.stop()

                def after_play_callback_builder():
                    ## Wrap this in a closure to keep it available even when it should be out of scope
                    current_active_play_request = active_play_request
                    
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

                logger.debug('Playing file at: {}, in channel: {}, in server: {}, for user: {}'.format(
                    self.active_play_request.file_path,
                    self.active_play_request.channel.name,
                    self.active_play_request.channel.guild.name,
                    self.active_play_request.member.name if self.active_play_request.member else None
                ))
                voice_client.play(self.active_play_request.audio, after=after_play_callback_builder())
                await self.next.wait()
            
            except Exception as e:
                logger.exception('Exception inside audio player event loop', exc_info=e)


class AudioPlayer(DiscoverableCog):
    ## Keys
    SKIP_PERCENTAGE_KEY = "skip_percentage"
    FFMPEG_PARAMETERS_KEY = "ffmpeg_parameters"
    FFMPEG_POST_PARAMETERS_KEY = "ffmpeg_post_parameters"


    def __init__(self, bot: commands.Bot, channel_timeout_handler, *args, **kwargs):
        self.bot = bot
        self.server_states = {}
        self.channel_timeout_handler = channel_timeout_handler
        self.dynamo_db = dynamo_manager.DynamoManager()

        ## Clamp between 0.0 and 1.0
        self.skip_percentage = max(min(float(CONFIG_OPTIONS.get(self.SKIP_PERCENTAGE_KEY, 0.5)), 1.0), 0.0)
        self.ffmpeg_parameters = CONFIG_OPTIONS.get(self.FFMPEG_PARAMETERS_KEY, "")
        self.ffmpeg_post_parameters = CONFIG_OPTIONS.get(self.FFMPEG_POST_PARAMETERS_KEY, "")

    ## Methods

    def get_server_state(self, ctx) -> ServerStateManager:
        '''Retrieves the server state for the provided server_id, or creates a new one if no others exist'''

        server_id = ctx.message.guild.id
        server_state = self.server_states.get(server_id, None)

        if (server_state is None):
            server_state = ServerStateManager(ctx, self.bot, self, self.channel_timeout_handler)
            self.server_states[server_id] = server_state

        return server_state


    def build_player(self, file_path: Path) -> discord.FFmpegPCMAudio:
        '''Builds an audio player for playing the file located at 'file_path'.'''

        return discord.FFmpegPCMAudio(
            str(file_path),
            before_options=self.ffmpeg_parameters,
            options=self.ffmpeg_post_parameters
        )

    ## Commands

    @commands.command(no_pm=True)
    async def skip(self, ctx, force = False):
        '''Vote to skip the current audio.'''

        state = self.get_server_state(ctx)

        ## Is the bot speaking?
        if(not state.is_playing()):
            await ctx.send("I'm not speaking at the moment.")
            return False

        ## Handle forced skips (should pretty much always be from an admin/bot owner)
        if (force):
            state.skip_audio()
            await ctx.send("<@{}> has skipped the audio.".format(ctx.message.author.id))
            return True

        ## Add a skip vote and tally it up!
        voter = ctx.message.author
        if(voter == state.active_play_request.member):
            state.skip_audio()
            await ctx.send("<@{}> skipped their own audio.".format(voter.id))
            return False

        elif(voter.id not in state.skip_votes):
            state.skip_votes.add(voter.id)

            ## Ensure all voters are still in the current channel (no drive-by skipping)
            active_members = await state.get_members()
            active_voters = [voter for voter in state.skip_votes if any(voter == member.id for member in active_members)]
            total_votes = len(active_voters)

            ## Determine if a skip should happen or not
            vote_percentage = total_votes / len(active_members)
            if(vote_percentage >= self.skip_percentage):
                state.skip_audio()
                await ctx.send("Skip vote passed! Skipping the current audio right now.")
                return True

            else:
                ## The total votes needed for a successful skip
                required_votes = math.ceil(len(active_members) * self.skip_percentage)

                raw = "Skip vote added! Currently at {} of {} votes."
                await ctx.send(raw.format(total_votes, required_votes))

        else:
            await ctx.send("<@{}> has already voted!".format(voter.id))


    ## Interface for playing the audio file for the invoker's channel
    async def play_audio(self, ctx, file_path: Path, target_member = None, callback: Callable = None):
        '''Plays the given audio file aloud to your channel'''

        ## Verify that the target/requester is in a channel
        if (not target_member or not isinstance(target_member, Member)):
            target_member = ctx.message.author

        voice_channel = None
        if (target_member.voice):   ## Handle users not in a voice channel
            voice_channel = target_member.voice.channel
        if(voice_channel is None):
            await ctx.send("<@{}> isn't in a voice channel.".format(target_member.id))
            return False

        ## Make sure file_path points to an actual file
        if (not file_path.is_file()):
            logger.error("Unable to play file at: {}, file doesn't exist or isn't a file.".format(file_path))
            await ctx.send("Sorry, <@{}>, that couldn't be played.".format(ctx.message.author.id))
            return False

        ## Get/Build a state for this audio, build the player, and add it to the state
        state = self.get_server_state(ctx)
        player = self.build_player(file_path)
        await state.add_play_request(AudioPlayRequest(ctx.message.author, voice_channel, player, file_path, callback))

        self.dynamo_db.put(dynamo_manager.CommandItem(
            ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))

        return True


    async def _play_audio_via_server_state(self, server_state: ServerStateManager, file_path: Path, callback: Callable = None):
        '''Internal method for playing audio without a requester. Instead it'll play from the active voice_client.'''

        ## Make sure file_path points to an actual file
        if (not file_path.is_file()):
            logger.error("Unable to play file at: {}, file doesn't exist or isn't a file.".format(file_path))
            return False

        ## Create a player for the audio file
        player = self.build_player(file_path)

        ## On successful player creation, build a AudioPlayRequest and push it into the queue
        play_request = AudioPlayRequest(None, server_state.ctx.voice_client.channel, player, file_path, callback)
        await server_state.add_play_request(play_request)

        return True

def main() -> ModuleInitializationStruct:
    return ModuleInitializationStruct(AudioPlayer, True)
