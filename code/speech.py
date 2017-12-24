import os
os.environ = {} # Remove env variables to give os.system a semblance of security
import sys
import re
import asyncio
import time
from math import ceil

import utilities
from discord import errors
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()


class TTSController:
    ## Keys
    TTS_FILE_KEY = "tts_file"
    TTS_FILE_PATH_KEY = "tts_file_path"
    TTS_OUTPUT_DIR_KEY = "tts_output_dir"
    TTS_OUTPUT_DIR_PATH_KEY = "tts_output_dir_path"
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
    TTS_FILE = CONFIG_OPTIONS.get(TTS_FILE_KEY, "say.exe")
    TTS_FILE_PATH = CONFIG_OPTIONS.get(TTS_FILE_PATH_KEY, os.sep.join([os.path.dirname(os.path.abspath(__file__)), TTS_FILE]))
    TTS_OUTPUT_DIR = CONFIG_OPTIONS.get(TTS_OUTPUT_DIR_KEY, "temp")
    TTS_OUTPUT_DIR_PATH = CONFIG_OPTIONS.get(TTS_OUTPUT_DIR_PATH_KEY, os.sep.join([utilities.get_root_path(), TTS_OUTPUT_DIR]))
    PREPEND = CONFIG_OPTIONS.get(PREPEND_KEY, "[:phoneme on]")
    APPEND = CONFIG_OPTIONS.get(APPEND_KEY, "")
    CHAR_LIMIT = CONFIG_OPTIONS.get(CHAR_LIMIT_KEY, 1250)
    NEWLINE_REPLACEMENT = CONFIG_OPTIONS.get(NEWLINE_REPLACEMENT_KEY, "[_<250,10>]")
    OUTPUT_EXTENSION = CONFIG_OPTIONS.get(OUTPUT_EXTENSION_KEY, "wav")
    WINE = CONFIG_OPTIONS.get(WINE_KEY, "wine")
    XVFB_PREPEND = CONFIG_OPTIONS.get(XVFB_PREPEND_KEY, "DISPLAY=:0.0")
    HEADLESS = CONFIG_OPTIONS.get(HEADLESS_KEY, False)


    def __init__(self, exe_path=None, **kwargs):
        self.exe_path = exe_path or kwargs.get(self.TTS_FILE_PATH_KEY, self.TTS_FILE_PATH)
        self.output_dir_path = kwargs.get(self.TTS_OUTPUT_DIR_PATH_KEY, self.TTS_OUTPUT_DIR_PATH)
        self.args = kwargs.get(self.ARGS_KEY, {})
        self.prepend = kwargs.get(self.PREPEND_KEY, self.PREPEND)
        self.append = kwargs.get(self.APPEND_KEY, self.APPEND)
        self.char_limit = int(kwargs.get(self.CHAR_LIMIT_KEY, self.CHAR_LIMIT))
        self.newline_replacement = kwargs.get(self.NEWLINE_REPLACEMENT_KEY, self.NEWLINE_REPLACEMENT)
        self.output_extension = kwargs.get(self.OUTPUT_EXTENSION_KEY, self.OUTPUT_EXTENSION)
        self.wine = kwargs.get(self.WINE_KEY, self.WINE)
        self.xvfb_prepend = kwargs.get(self.XVFB_PREPEND_KEY, self.XVFB_PREPEND)
        self.is_headless = kwargs.get(self.HEADLESS_KEY, self.HEADLESS)

        self.paths_to_delete = []

        if(self.output_dir_path):
            self._init_dir()


    def __del__(self):
        self._init_dir()


    def _init_dir(self):
        if(not os.path.exists(self.output_dir_path)):
            os.makedirs(self.output_dir_path)
        else:
            for root, dirs, files in os.walk(self.output_dir_path, topdown=False):
                for file in files:
                    try:
                        os.remove(os.sep.join([root, file]))
                    except OSError as e:
                        utilities.debug_print("Error removing file: {}".format(file), e, debug_level=2)


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
        for index, path in enumerate(self.paths_to_delete):
            try:
                os.remove(path)
            except FileNotFoundError:
                ## The goal was to remove the file, and as long as it doesn't exist then we're good.
                continue
            except Exception as e:
                utilities.debug_print("Error deleting file:", path, type(e).__name__, e, debug_level=1)
                to_delete.append(path)

        self.paths_to_delete = to_delete[:]

        return True


    async def save(self, message, ignore_char_limit=False):
        ## Validate output directory
        if(not self.output_dir_path):
            utilities.debug_print("Unable to save without output_dir_path set. See {}.__init__".format(self.__name__), debug_level=0)
            return None

        ## Check message size
        if(not self.check_length(message) and not ignore_char_limit):
            return None

        ## Generate and validate filename
        output_file_path = os.sep.join([self.output_dir_path, 
                                        self._generate_unique_file_name(self.output_extension)])

        ## Parse options and message
        save_option = '-w "{}"'.format(output_file_path)
        message = self._parse_message(message)

        ## Format and invoke
        args = '{} {} "{}"'.format(
            self.exe_path,
            save_option,
            message
        )

        ## Prepend the windows emulator if using linux (I'm aware of what WINE means)
        if(utilities.is_linux()):
            args = "{} {}".format(self.wine, args)

        ## Prepend the fake display created with Xvfb if running headless
        if(self.is_headless):
            args = "{} {}".format(self.xvfb_prepend, args)

        retval = os.system(args)

        if(retval == 0):
            return output_file_path
        else:
            return None


class SpeechEntry:
    def __init__(self, requester, channel, player, file_path):
        self.requester = requester
        self.channel = channel
        self.player = player
        self.file_path = file_path


    def __str__(self):
        return "'{}' in '{}' wants '{}'".format(self.requester, self.channel, self.file_path)


class SpeechState:
    def __init__(self, bot, join_channel, remove_file):
        self.bot = bot
        self.voice_client = None
        self.current_speech = None
        self.join_channel = join_channel
        self.remove_file = remove_file
        self.next = asyncio.Event()
        self.skip_votes = set() # set of users that voted to skip
        self.speech_queue = asyncio.Queue()
        self.speech_player = self.bot.loop.create_task(self.speech_player())
        self.last_speech_time = self.get_current_time()

    ## Property(s)

    @property
    def player(self):
        return self.current_speech.player

    ## Methods

    ## Calculates the current UTC time in seconds
    def get_current_time(self):
        return int(time.time())


    ## Returns a list of members in the current voice channel
    async def get_members(self):
        return self.current_speech.channel.voice_members


    ## Returns a bool to determine if the bot is speaking in this state.
    def is_speaking(self):
        if(self.voice_client is None or self.current_speech is None):
            return False

        return not self.player.is_done()


    ## Skips the currently playing speech (magic happens in speech_player)
    async def skip_speech(self):
        self.skip_votes.clear()
        if(self.is_speaking()):
            self.player.stop()


    ## Triggers the next speech in speech_queue to be played
    def next_speech(self):
        self.bot.loop.call_soon_threadsafe(self.next.set)

        if(self.current_speech):
            self.remove_file(self.current_speech.file_path)


    ## Speech player event loop task
    async def speech_player(self):
        while(True):
            self.next.clear()
            self.current_speech = await self.speech_queue.get()
            await self.join_channel(self.current_speech.channel)
            self.last_speech_time = self.get_current_time()
            self.current_speech.player.start()
            await self.next.wait()


class Speech:
    ## Keys
    DELETE_COMMANDS_KEY = "delete_commands"
    SKIP_VOTES_KEY = "skip_votes"
    SKIP_PERCENTAGE_KEY = "skip_percentage"
    SPEECH_STATES_KEY = "speech_states"
    FFMPEG_BEFORE_OPTIONS_KEY = "ffmpeg_before_options"
    FFMPEG_OPTIONS_KEY = "ffmpeg_options"
    CHANNEL_TIMEOUT_KEY = "channel_timeout"

    ## Defaults
    DELETE_COMMANDS = CONFIG_OPTIONS.get(DELETE_COMMANDS_KEY, False)
    SKIP_VOTES = CONFIG_OPTIONS.get(SKIP_VOTES_KEY, 3)
    SKIP_PERCENTAGE = CONFIG_OPTIONS.get(SKIP_PERCENTAGE_KEY, 33)
    # Before options are command line options (ex. "-ac 2") inserted before FFMpeg's -i flag
    FFMPEG_BEFORE_OPTIONS = CONFIG_OPTIONS.get(FFMPEG_BEFORE_OPTIONS_KEY, "")
    # Options are command line options inserted after FFMpeg's -i flag
    FFMPEG_OPTIONS = CONFIG_OPTIONS.get(FFMPEG_OPTIONS_KEY, "")
    CHANNEL_TIMEOUT = CONFIG_OPTIONS.get(CHANNEL_TIMEOUT_KEY, 15 * 60)


    def __init__(self, bot, tts_controller=None, **kwargs):
        self.bot = bot
        self.tts_controller = tts_controller or TTSController()
        self.speech_states = {}
        self.save = self.tts_controller.save
        self.delete = self.tts_controller.delete
        self.delete_commands = kwargs.get(self.DELETE_COMMANDS_KEY, self.DELETE_COMMANDS)
        self.skip_votes = int(kwargs.get(self.SKIP_VOTES_KEY, self.SKIP_VOTES))
        self.skip_percentage = int(kwargs.get(self.SKIP_PERCENTAGE_KEY, self.SKIP_PERCENTAGE))
        self.ffmpeg_before_options = kwargs.get(self.FFMPEG_BEFORE_OPTIONS_KEY, self.FFMPEG_BEFORE_OPTIONS)
        self.ffmpeg_options = kwargs.get(self.FFMPEG_OPTIONS_KEY, self.FFMPEG_OPTIONS)
        self.channel_timeout = int(kwargs.get(self.CHANNEL_TIMEOUT_KEY, self.CHANNEL_TIMEOUT))

    ## Methods

    ## Removes the players in all of the speech_states, and disconnects any voice_clients
    def __unload(self):
        for state in self.speech_states.values():
            try:
                state.speech_player.cancel()
                if(state.voice_client):
                    self.bot.loop.create_task(state.voice_client.disconnect())
                #state.speech_player.stop()
            except:
                pass


    ## Returns/creates a speech state in the speech_states dict with key of server.id
    def get_speech_state(self, server):
        state = self.speech_states.get(server.id)
        if(state is None):
            state = SpeechState(self.bot, self.join_channel, self.delete)
            self.speech_states[server.id] = state

        return state


    ## Creates a voice_client in state.voice_client
    async def create_voice_client(self, channel):
        voice_client = await self.bot.join_voice_channel(channel)
        state = self.get_speech_state(channel.server)
        state.voice_client = voice_client


    ## Tries to get the bot to join a channel
    async def join_channel(self, channel):
        state = self.get_speech_state(channel.server)

        ## Check if we've already got a voice client
        if(state.voice_client):
            ## Check if bot is already in the desired channel
            if(state.voice_client.channel == channel):
                return True

            ## Otherwise, move it into the desired channel
            try:
                await state.voice_client.move_to(channel)
            except Exception as e:
                utilities.debug_print("Voice client exists", e, debug_level=2)
                return False
            else:
                return True

        ## Otherwise, create a new one
        try:
            await self.create_voice_client(channel)
        except (discord.ClientException, discord.InvalidArgument) as e:
            utilities.debug_print("Voice client doesn't exist", e, debug_level=2)
            return False
        else:
            return True


    ## Tries to get the bot to leave a state's channel
    async def leave_channel(self, channel):
        ## Todo: the channel and state manipulation for this method is no bueno. Move to kwargs or something
        state = self.get_speech_state(channel.server)

        if(state.voice_client):
            ## Disconnect and un-set the voice client
            await state.voice_client.disconnect()
            state.voice_client = None
            return True
        else:
            return False


    ## Tries to delete the command message
    async def attempt_delete_command_message(self, message):
        if(self.delete_commands):
            try:
                await self.bot.delete_message(message)
            except errors.Forbidden:
                utilities.debug_print("Bot doesn't have permission to delete the message", debug_level=3)


    ## Tries to disonnect the bot from the given state's voice channel if it hasn't been used in a while.
    async def attempt_leave_channel(self, state):
        await asyncio.sleep(self.channel_timeout)
        if(state.last_speech_time + self.channel_timeout <= state.get_current_time() and state.voice_client):
            utilities.debug_print("Leaving channel", debug_level=4)
            await self.leave_channel(state.voice_client.channel)


    ## Checks if a given command fits into the back of a string (ex. '\say' matches 'say')
    def is_matching_command(self, string, command):
        to_check = string[len(command):]
        return (command == to_check)


<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> master
    ## Replaces user.id mention strings with their actual names
    def replace_mentions(self, message_ctx, string):
        def replace_id_with_string(string, discord_id, replacement):
            match = re.search("<@[!|&]?({})>".format(discord_id), string)
            if(match):
                start, end = match.span(0)
                string = string[:start] + replacement + string[end:]

            return string

        for user in message_ctx.mentions:
            string = replace_id_with_string(string, user.id, user.nick if user.nick else user.name)

        for channel in message_ctx.channel_mentions:
            string = replace_id_with_string(string, channel.id, channel.name)

        for role in message_ctx.role_mentions:
            string = replace_id_with_string(string, role.id, role.name)

        return string

<<<<<<< HEAD
=======
>>>>>>> a5760a7f5b57241e4c2543b0a71ed4210d93257e
=======
>>>>>>> master
    ## Commands

    ## Tries to summon the bot to a user's channel
    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""

        ## Check that the requester is in a voice channel
        summoned_channel = ctx.message.author.voice_channel
        if(summoned_channel is None):
            await self.bot.say("{} isn't in a voice channel.".format(ctx.message.author))
            return False

        ## Attempt to delete the command message
        await self.attempt_delete_command_message(ctx.message)

        return await self.join_channel(summoned_channel)


    ## Initiate/Continue a vote to skip on the currently playing speech
    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip the current speech."""

        state = self.get_speech_state(ctx.message.server)
        if(not state.is_speaking()):
            await self.bot.say("I'm not speaking at the moment.")
            return False

        voter = ctx.message.author
        if(voter == state.current_speech.requester):
            await self.bot.say("<@{}> skipped their own speech.".format(voter.id))
            await state.skip_speech()
            ## Attempt to delete the command message
            await self.attempt_delete_command_message(ctx.message)
            return False
        elif(voter.id not in state.skip_votes):
            state.skip_votes.add(voter.id)

            ## Todo: filter total_votes by members actually in the channel
            total_votes = len(state.skip_votes)
            total_members = len(await state.get_members()) - 1  # Subtract one for the bot itself
            vote_percentage = ceil((total_votes / total_members) * 100)

            if(total_votes >= self.skip_votes or vote_percentage >= self.skip_percentage):
                await self.bot.say("Skip vote passed, skipping current speech.")
                await state.skip_speech()
                return True
            else:
                raw = "Skip vote added, currently at {}/{} or {}%/{}%"
                await self.bot.say(raw.format(total_votes, self.skip_votes, vote_percentage, self.skip_percentage))

        else:
            await self.bot.say("<@{}> has already voted!".format(voter.id))


    ## Starts the TTS process! Creates and stores a ffmpeg player for the message to be played
    @commands.command(pass_context=True, no_pm=True)
    async def say(self, ctx, *, message, ignore_char_limit=False):
        """Speaks your text aloud to your channel."""

        ## Todo: look into memoization of speech. Phrases.py's speech is a perfect candidate

        ## Check that the requester is in a voice channel
        voice_channel = ctx.message.author.voice_channel
        if(voice_channel is None):
            await self.bot.say("<@{}> isn't in a voice channel.".format(ctx.message.author.id))
            return False

        ## Make sure the message isn't too long
        if(not self.tts_controller.check_length(message) and not ignore_char_limit):
            await self.bot.say("Keep phrases less than {} characters.".format(self.tts_controller.char_limit))
            return False

        state = self.get_speech_state(ctx.message.server)
        if(state.voice_client is None):
            ## Todo: Handle exception if unable to create a voice client
            await self.create_voice_client(voice_channel)

        message = self.replace_mentions(ctx.message, message)

        try:
            ## Create a .wav file of the message
            wav_path = await self.save(message, ignore_char_limit)
            if(wav_path):
                ## Create a player for the .wav
                player = state.voice_client.create_ffmpeg_player(
                    wav_path,
                    before_options=self.ffmpeg_before_options,
                    options=self.ffmpeg_options,
                    after=state.next_speech
                )
            else:
                raise RuntimeError("Unable to save a proper .wav file.")
        except Exception as e:
            utilities.debug_print("Exception in say():", e, debug_level=0)
            await self.bot.say("Unable to say the last message. Sorry, <@{}>.".format(ctx.message.author.id))
            return False
        else:
            ## On successful player creation, build a SpeechEntry and push it into the queue
            await state.speech_queue.put(SpeechEntry(ctx.message.author, voice_channel, player, wav_path))

            ## Start a timeout to disconnect the bot if the bot hasn't spoken in a while
            await self.attempt_leave_channel(state)

            ## Attempt to delete the command message
            await self.attempt_delete_command_message(ctx.message)

            return True
