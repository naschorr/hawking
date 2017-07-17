import os
os.environ = {} # Remove env variables to give os.system a semblance of security
import sys
import subprocess
import asyncio
import time
import json

import discord
from discord.ext import commands
from phrases import Phrases

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

## Config
## Bot Config
ACTIVATION_STR = "\\"
DESCRIPTION_STR = "A retro TTS bot for Discord (Alpha)\n Visit https://github.com/naschorr/hawking"
## Commands Config
SKIP_VOTES = 3
SKIP_PERCENTAGE = 33
## Base Config
ROOT_PATH = os.sep.join(os.path.realpath(__file__).split(os.path.sep)[:-2])
PHRASES_FILE = "phrases.json"
PHRASES_FILE_PATH = os.sep.join([ROOT_PATH, PHRASES_FILE])
TOKEN_FILE = "token.json"
TOKEN_FILE_PATH = os.sep.join([ROOT_PATH, TOKEN_FILE])
TOKEN_KEY = "token"
## DECTalk Config
DECTALK_DIR_PATH = os.path.dirname(os.path.abspath(__file__))   ## Same dir as this script
DECTALK_EXE = "say.exe"
DECTALK_EXE_PATH = os.sep.join([DECTALK_DIR_PATH, DECTALK_EXE])
DECTALK_OUTPUT_DIR = "temp"
DECTALK_OUTPUT_DIR_PATH = os.sep.join([ROOT_PATH, DECTALK_OUTPUT_DIR])
DECTALK_PREPEND = "[:phoneme on]"
DECTALK_APPEND = ""
CHAR_LIMIT = 1500
NEWLINE_REPLACEMENT = "[_<250,10>]"


class DECTalkController:
    ## Keys
    OUTPUT_DIR_PATH_KEY = "output_dir_path"
    ARGS_KEY = "args"
    PREPEND_KEY = "prepend"
    APPEND_KEY = "append"
    CHAR_LIMIT_KEY = "char_limit"
    NEWLINE_REPLACEMENT_KEY = "newline_replacement"

    ## Config
    CHAR_LIMIT = CHAR_LIMIT
    NEWLINE_REPLACEMENT = NEWLINE_REPLACEMENT
    OUTPUT_EXTENSION = "wav"


    def __init__(self, exe_path, **kwargs):
        self.exe_path = exe_path
        self.output_dir_path = kwargs.get(self.OUTPUT_DIR_PATH_KEY)
        self.args = kwargs.get(self.ARGS_KEY, {})
        self.prepend = kwargs.get(self.PREPEND_KEY)
        self.append = kwargs.get(self.APPEND_KEY)
        self.char_limit = kwargs.get(self.CHAR_LIMIT_KEY, self.CHAR_LIMIT)
        self.newline_replacement = kwargs.get(self.NEWLINE_REPLACEMENT_KEY, self.NEWLINE_REPLACEMENT)
        self.output_extension = self.OUTPUT_EXTENSION

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

    ## Config
    SKIP_VOTES = SKIP_VOTES
    SKIP_PERCENTAGE = SKIP_PERCENTAGE


    def __init__(self, bot, dectalk_controller, **kwargs):
        self.bot = bot
        self.speech_states = {}
        self.dectalk = dectalk_controller
        self.save = self.dectalk.save
        self.delete = self.dectalk.delete
        self.skip_votes = kwargs.get(self.SKIP_VOTES_KEY, self.SKIP_VOTES)
        self.skip_percentage = kwargs.get(self.SKIP_PERCENTAGE_KEY, self.SKIP_PERCENTAGE)

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
            vote_percentage = round((total_votes / total_members) * 100)

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
            await self.bot.say("{} isn't in a voice channel.".format(ctx.message.author))
            return False

        ## Make sure the message isn't too long
        if(not self.dectalk.check_length(message)):
            await self.bot.say("Keep phrases less than {} characters.".format(self.dectalk.char_limit))
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

## Main

def get_token():
    with open(TOKEN_FILE_PATH, "r") as fd:
        return json.load(fd)[TOKEN_KEY]


def main():
    ## Todo: Customize the help screen (commands.HelpFormatter)

    ## Init the bot
    bot = commands.Bot(
        command_prefix=commands.when_mentioned_or(ACTIVATION_STR),
        description=DESCRIPTION_STR
    )
    dectalk_controller = DECTalkController(DECTALK_EXE_PATH, output_dir_path=DECTALK_OUTPUT_DIR_PATH, prepend=DECTALK_PREPEND)
    bot.add_cog(Speech(bot, dectalk_controller))
    bot.add_cog(Phrases(bot, PHRASES_FILE_PATH, pass_context=True, no_pm=True))

    @bot.event
    async def on_ready():
        print("Logged in as '{}' (id:{})".format(bot.user.name, bot.user.id))

    ## Blocking execute
    bot.run(get_token())


if(__name__ == "__main__"):
    main()