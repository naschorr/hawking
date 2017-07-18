import os
os.environ = {} # Remove env variables to give os.system a semblance of security
import sys
import subprocess
import asyncio
import time
import json
from math import ceil

import discord
from discord.ext import commands

import utilities
from phrases import Phrases
from admin import Admin

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

## Config
CONFIG_OPTIONS = utilities.load_config()


class TTSController:
    ## Keys
    OUTPUT_DIR_PATH_KEY = "output_dir_path"
    ARGS_KEY = "args"
    PREPEND_KEY = "prepend"
    APPEND_KEY = "append"
    CHAR_LIMIT_KEY = "char_limit"
    NEWLINE_REPLACEMENT_KEY = "newline_replacement"
    OUTPUT_EXTENSION_KEY = "output_extension"

    ## Defaults
    PREPEND = CONFIG_OPTIONS.get(PREPEND_KEY, "[:phoneme on]")
    APPEND = CONFIG_OPTIONS.get(APPEND_KEY, "")
    CHAR_LIMIT = CONFIG_OPTIONS.get(CHAR_LIMIT_KEY, 1250)
    NEWLINE_REPLACEMENT = CONFIG_OPTIONS.get(NEWLINE_REPLACEMENT_KEY, "[_<250,10>]")
    OUTPUT_EXTENSION = CONFIG_OPTIONS.get(OUTPUT_EXTENSION_KEY, "wav")


    def __init__(self, exe_path, **kwargs):
        self.exe_path = exe_path
        self.output_dir_path = kwargs.get(self.OUTPUT_DIR_PATH_KEY)
        self.args = kwargs.get(self.ARGS_KEY, {})
        self.prepend = kwargs.get(self.PREPEND_KEY, self.PREPEND)
        self.append = kwargs.get(self.APPEND_KEY, self.APPEND)
        self.char_limit = int(kwargs.get(self.CHAR_LIMIT_KEY, self.CHAR_LIMIT))
        self.newline_replacement = kwargs.get(self.NEWLINE_REPLACEMENT_KEY, self.NEWLINE_REPLACEMENT)
        self.output_extension = kwargs.get(self.OUTPUT_EXTENSION_KEY, self.OUTPUT_EXTENSION)

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
                    os.remove(os.sep.join([root, file]))


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
            except Exception as e:
                if(file_path != path):
                    ## If the file to delete isn't the one that's (probably) still loaded, then 
                    ## definitely display something.
                    print("Error removing path:", path)

                to_delete.append(path)

        self.paths_to_delete = to_delete[:]
        return True


    async def save(self, message):
        ## Validate output directory
        if(not self.output_dir_path):
            print("Unable to save without output_dir_path set. See {}.__init__".format(self.__name__))
            return None

        ## Check message size
        if(not self.check_length(message)):
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

    ## Property(s)

    @property
    def player(self):
        return self.current_speech.player

    ## Methods

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
            self.current_speech.player.start()
            await self.next.wait()


class Speech:
    ## Keys
    SKIP_VOTES_KEY = "skip_votes"
    SKIP_PERCENTAGE_KEY = "skip_percentage"

    ## Defaults
    SKIP_VOTES = CONFIG_OPTIONS.get(SKIP_VOTES_KEY, 3)
    SKIP_PERCENTAGE = CONFIG_OPTIONS.get(SKIP_PERCENTAGE_KEY, 33)


    def __init__(self, bot, tts_controller, **kwargs):
        ## Todo: add admin discord id to config, then have a reload phrases command for admin users only?

        self.bot = bot
        self.speech_states = {}
        self.tts_controller = tts_controller
        self.save = self.tts_controller.save
        self.delete = self.tts_controller.delete
        self.skip_votes = int(kwargs.get(self.SKIP_VOTES_KEY, self.SKIP_VOTES))
        self.skip_percentage = int(kwargs.get(self.SKIP_PERCENTAGE_KEY, self.SKIP_PERCENTAGE))

    ## Methods

    ## Returns/creates a speech state in the speech_states dict with key of server.id
    def get_speech_state(self, server):
        state = self.speech_states.get(server.id)
        if(state is None):
            state = SpeechState(self.bot, self.join_channel, self.delete)
            self.speech_states[server.id] = state

        return state


    ## Removes the players in all of the speech_states
    def __unload(self):
        for state in self.speech_states.values():
            try:
                state.speech_player.cancel()
                if(state.speech):
                    self.bot.loop.create_task(state.speech.disconnect())
            except:
                pass


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
                print("Voice client exists", e)
                return False
            else:
                return True

        ## Otherwise, create a new one
        try:
            await self.create_voice_client(channel)
        except (discord.ClientException, discord.InvalidArgument) as e:
            print("Voice client doesn't exist", e)
            return False
        else:
            return True

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
                raw = "Skip vote added, currently at {}/{} or {}%"
                await self.bot.say(raw.format(total_votes, self.skip_votes, vote_percentage))
        else:
            await self.bot.say("<@{}> has already voted!".format(voter.id))


    ## Starts the TTS process! Creates and stores a ffmpeg player for the message to be played
    @commands.command(pass_context=True, no_pm=True)
    async def say(self, ctx, *, message):
        """Speaks your text aloud to your channel."""

        ## Todo: look into memoization of speech. Phrases.py's speech is a perfect candidate

        ## Check that the requester is in a voice channel
        voice_channel = ctx.message.author.voice_channel
        if(voice_channel is None):
            await self.bot.say("<@{}> isn't in a voice channel.".format(ctx.message.author.id))
            return False

        ## Make sure the message isn't too long
        if(not self.tts_controller.check_length(message)):
            await self.bot.say("Keep phrases less than {} characters.".format(self.tts_controller.char_limit))
            return False

        state = self.get_speech_state(ctx.message.server)
        if(state.voice_client is None):
            await self.create_voice_client(voice_channel)

        try:
            ## Create a .wav file of the message
            wav_path = await self.save(message)
            if(wav_path):
                ## Create a player for the .wav
                player = state.voice_client.create_ffmpeg_player(wav_path, after=state.next_speech)
        except Exception as e:
            print("Exception in say():", e)
            return False
        else:
            ## On successful player creation, build a SpeechEntry and push it into the queue
            await state.speech_queue.put(SpeechEntry(ctx.message.author, voice_channel, player, wav_path))
            return True

class Hawking:
    ## Keys and Defaults
    ## Basically, any given class can be configured by changing the respective value for the
    ## desired key in config.json (see the Keys section at the top of each class for a list of
    ## keys). However, if you want to use Hawking as a part of something else, you may want to
    ## dynamically configure objects as necessary. Thus, you can also instantiate classes with
    ## keyworded arguments, which will then override any existing defaults, or config.json data.
    ## The existing defaults in each class are sort of like a fallback, in case the config.json is
    ## broken in some way.

    ## Keys
    ACTIVATION_STR_KEY = "activation_str"
    DESCRIPTION_KEY = "description"
    TOKEN_KEY = "token"
    TOKEN_FILE_KEY = "token_file"
    TOKEN_FILE_PATH_KEY = "token_file_path"
    PHRASES_FILE_KEY = "phrases_file"
    PHRASES_FILE_PATH_KEY = "phrases_file_path"
    TTS_FILE_KEY = "tts_file"
    TTS_FILE_PATH_KEY = "tts_file_path"
    TTS_OUTPUT_DIR_KEY = "tts_output_dir"
    TTS_OUTPUT_DIR_PATH_KEY = "tts_output_dir_path"

    ## Defaults
    ACTIVATION_STR = CONFIG_OPTIONS.get(ACTIVATION_STR_KEY, "\\")
    DESCRIPTION = CONFIG_OPTIONS.get(DESCRIPTION_KEY, "A retro TTS bot for Discord (Alpha)\n Visit https://github.com/naschorr/hawking")
    TOKEN_FILE = CONFIG_OPTIONS.get(TOKEN_FILE_KEY, "token.json")
    TOKEN_FILE_PATH = CONFIG_OPTIONS.get(TOKEN_FILE_PATH_KEY, os.sep.join([utilities.get_root_path(), TOKEN_FILE]))
    PHRASES_FILE = CONFIG_OPTIONS.get(PHRASES_FILE_KEY, "phrases.json")
    PHRASES_FILE_PATH = CONFIG_OPTIONS.get(PHRASES_FILE_PATH_KEY, os.sep.join([utilities.get_root_path(), PHRASES_FILE]))
    TTS_FILE = CONFIG_OPTIONS.get(TTS_FILE_KEY, "say.exe")
    TTS_FILE_PATH = CONFIG_OPTIONS.get(TTS_FILE_PATH_KEY, os.sep.join([os.path.dirname(os.path.abspath(__file__)), TTS_FILE]))
    TTS_OUTPUT_DIR = CONFIG_OPTIONS.get(TTS_OUTPUT_DIR_KEY, "temp")
    TTS_OUTPUT_DIR_PATH = CONFIG_OPTIONS.get(TTS_OUTPUT_DIR_PATH_KEY, os.sep.join([utilities.get_root_path(), TTS_OUTPUT_DIR]))


    ## Initialize the bot, and add base cogs
    def __init__(self, **kwargs):
        self.activation_str = kwargs.get(self.ACTIVATION_STR_KEY, self.ACTIVATION_STR)
        self.description = kwargs.get(self.DESCRIPTION_KEY, self.DESCRIPTION)
        self.token_file_path = kwargs.get(self.TOKEN_FILE_PATH_KEY, self.TOKEN_FILE_PATH)
        self.phrases_file_path = kwargs.get(self.PHRASES_FILE_PATH_KEY, self.PHRASES_FILE_PATH)
        self.tts_file_path = kwargs.get(self.TTS_FILE_PATH_KEY, self.TTS_FILE_PATH)
        self.tts_output_dir_path = kwargs.get(self.TTS_OUTPUT_DIR_PATH_KEY, self.TTS_OUTPUT_DIR_PATH)

        ## Init the bot
        self.bot = commands.Bot(
            command_prefix=commands.when_mentioned_or(self.activation_str),
            description=self.description
        )

        ## Prepare the required cogs
        tts_controller = TTSController(
            self.tts_file_path,
            output_dir_path=self.tts_output_dir_path
        )
        self.add_cog(Speech(self.bot, tts_controller))
        self.add_cog(Phrases(self.bot, self.phrases_file_path, pass_context=True, no_pm=True))
        self.add_cog(Admin(self.bot))

        @self.bot.event
        async def on_ready():
            print("Logged in as '{}' (id:{})".format(self.bot.user.name, self.bot.user.id))

    ## Methods

    ## Add an arbitary cog to the bot
    def add_cog(self, cls):
        self.bot.add_cog(cls)


    ## Run the bot
    def run(self):
        self.bot.run(utilities.load_json(self.token_file_path)[self.TOKEN_KEY])


if(__name__ == "__main__"):
    hawking = Hawking()
    # hawking.add_cog(ArbitaryClass(*args, **kwargs))
    hawking.run()