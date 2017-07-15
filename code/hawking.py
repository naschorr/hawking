import os
import sys
import subprocess
import asyncio
import time
import json
import discord
from discord.ext import commands

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('opus')

## Config
## Todo: fix this hot mess
ACTIVATION_STRING = "\\"
DESCRIPTION = "A DECTalk interface for Discord (Alpha)"
ROOT_DIR = os.sep.join(os.path.realpath(__file__).split(os.path.sep)[:-2])
TOKEN_JSON = "token.json"
TOKEN_JSON_PATH = os.sep.join([ROOT_DIR, TOKEN_JSON])
TOKEN_KEY = "token"
DECTALK_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
DECTALK_EXE = "say.exe"
DECTALK_EXE_PATH = os.sep.join([DECTALK_DIR_PATH, DECTALK_EXE])
DECTALK_ARGS = "-w"
DECTALK_PREPEND = "[:phoneme on] "
DECTALK_APPEND = ""
DECTALK_PAUSE_SIM = "    "
DECTALK_FILE_OUTPUT_FORMAT = "{}.wav"
TEMP_DIR = "temp"
TEMP_DIR_PATH = os.sep.join([ROOT_DIR, TEMP_DIR])
CHAR_LIMIT = 1000
os.environ = {} # Remove env variables to give os.system a semblance of security


class SpeechEntry:
    def __init__(self, message, channel, player, file_path):
        self.channel = channel
        self.message = message
        self.player = player
        self.file_path = file_path


    def __str__(self):
        return "'{}' in '{}'".format(self.message, self.channel)


class SpeechState:
    def __init__(self, bot, join_channel, remove_file):
        self.bot = bot
        self.voice_client = None
        self.current_speech = None
        self.join_channel = join_channel
        self.remove_file = remove_file
        self.next = asyncio.Event()
        self.speech_queue = asyncio.Queue()
        self.speech_player = self.bot.loop.create_task(self.speech_player())


    @property
    def player(self):
        return self.current_speech.player


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
    def __init__(self, bot):
        self.bot = bot
        self.speech_states = {}

        self.dectalk_exe = DECTALK_EXE_PATH
        self.dectalk_args = DECTALK_ARGS
        self.prepend_string = DECTALK_PREPEND
        self.append_string = DECTALK_APPEND
        self.temp_dir_path = TEMP_DIR_PATH
        self.dectalk_pause_sim = DECTALK_PAUSE_SIM
        self.dectalk_file_output = DECTALK_FILE_OUTPUT_FORMAT
        self.char_limit = CHAR_LIMIT

    ## Methods

    ## Returns/creates a speech state in the speech_states dict with key of server.id
    def get_speech_state(self, server):
        state = self.speech_states.get(server.id)
        if(state is None):
            state = SpeechState(self.bot, self.join_channel, self.remove_file)
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


    ## Removes a file located at path
    def remove_file(self, path):
        if(os.path.isfile(path)):
            os.remove(path)

        return True


    ## This whole method is kind of bad. todo: fix it
    async def save_wav(self, message, *args):
        ## Helps to ensure the system isn't constantly fighting for 'temp.wav'
        file_uniquify = ""
        for arg in args:
            file_uniquify += str(arg).replace(" ", "").lower()
        file_uniquify += str(int(time.time() * 1000))

        ## Add temp/ if it doesn't exist
        if(not os.path.exists(self.temp_dir_path)):
            os.makedirs(self.temp_dir_path)

        ## Build path for .wav file in temp/ folder
        temp_file_path = os.sep.join([self.temp_dir_path, self.dectalk_file_output.format(file_uniquify)])

        ## Verify that it doesn't already exist
        self.remove_file(temp_file_path)

        ## Apostrophes trip up the tts
        args = '{} {} "{}" "{}{}{}"'.format(
            self.dectalk_exe,
            self.dectalk_args,  ## Todo: fix this naming
            temp_file_path,
            self.prepend_string,
            message.replace("\n", self.dectalk_pause_sim).replace('"', ""), # Todo: dedicated message parser
            self.append_string
        )

        ## Invoke say.exe
        retval = os.system(args)

        if(retval == 0):
            return temp_file_path
        else:
            return None


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


    ## Starts the TTS process! Creates and stores a ffmpeg player for the message to be played
    @commands.command(pass_context=True, no_pm=True)
    async def say(self, ctx, *, message):
        """Speaks your text using the DECTalk TTS engine."""

        ## Check that the requester is in a voice channel
        voice_channel = ctx.message.author.voice_channel
        if(voice_channel is None):
            await self.bot.say("{} isn't in a voice channel.".format(ctx.message.author))
            return False

        ## Make sure the message isn't too long
        if(len(message) > self.char_limit):
            await self.bot.say("Keep phrases less than {} characters.".format(self.char_limit))
            return False

        state = self.get_speech_state(ctx.message.server)
        if(state.voice_client is None):
            await self.create_voice_client(voice_channel)

        try:
            ## Create a .wav file of the message
            wav_path = await self.save_wav(message, ctx.message.server, ctx.message.author)
            if(wav_path):
                ## Create a player for the .wav
                player = state.voice_client.create_ffmpeg_player(wav_path, after=state.next_speech)
        except Exception as e:
            print("Exception in say():", e)
            return False
        else:
            ## On successful player creation, build a SpeechEntry and push it into the queue
            await state.speech_queue.put(SpeechEntry(message, voice_channel, player, wav_path))
            return True


class SpeechPreset:
    def __init__(self, bot):
        self.bot = bot
        self.speech = self.bot.get_cog("Speech")

    @commands.command(pass_context=True, no_pm=True)
    async def pizza(self, ctx):
        """Time for some pizza"""
        message = (
            "[:nh]I'm gonna eat a pizza. [:dial67589340] Hi, can i order a pizza?"
            "[:nv]no! [:nh]why? [:nv] cuz you are john madden![:np]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def skeletons(self, ctx):
        """Spooky and scary"""
        message = (
            "[spuh<300,19>kiy<300,19>skeh<300,18>riy<300,18>skeh<300,11>lleh<175,14>tih<200,11>ns]. "
            "[seh<300,11>nd][shih<100,19>ver<500,19>sdaw<300,18>nyur<300,18>spay<300,11>n]. "
            "[shriy<300,19>kiy<300,19>ng][skow<300,18>swih<300,18>ll]"
            "[shah<300,11>kyur<300,14>sow<300,11>ll]"
            "[siy<300,14>llyur<300,16>duh<300,13>mtuh<300,14>nay<300,11>t]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def taps(self, ctx):
        """o7"""
        message = (
            "[pr<600,18>][pr<200,18>][pr<1800,23>_>pr<600,18>][pr<300,23>][pr<1800,27>]"
            "[pr<600,18>][pr<300,23>][pr<1200,27>][pr<600,18>][pr<300,23>][pr<1200,27>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def birthday(self, ctx):
        """A very special day"""
        message = (
            "[hxae<300,10>piy<300,10>brr<600,12>th<100>dey<600,10>tuw<600,15>yu<1200,14>_<120>]"
            "[hxae<300,10>piy<300,10>brr<600,12>th<100>dey<600,10>tuw<600,17>yu<1200,15>_<120>]"
            "[hxae<300,10>piy<300,10>brr<600,22>th<100>dey<600,19>"
            "jh<100>aa<600,15>n<100>m<100>ae<600,14>d<50>dih<600,12>n]"
            "[hxae<300,20>piy<300,20>brr<600,19>th<100>dey<600,15>tuw<600,17>yu<1200,15>_<120>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def mamamia(self, ctx):
        """Could you handle that, dear?"""
        message = (
            "mamma mia, poppa pia, baby got the dy[aa<999,999>]reeeeeeeeeaaaaaaaaaa"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def imperial(self, ctx):
        """Marching along"""
        message = (
            "[dah<600,20>][dah<600,20>][dah<600,20>][dah<500,16>][dah<130,23>][dah<600,20>]"
            "[dah<500,16>][dah<130,23>][dah<600,20>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def daisy(self, ctx):
        """I'm afraid I can't do that."""
        message = (
            "[dey<600,24>ziy<600,21>dey<600,17>ziy<600,12>gih<200,14>vmiy<200,16>yurr<200,17>"
            "ah<400,14>nsrr<200,17>duw<1200,12>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def ateam(self, ctx):
        """I love it when a plan comes together!"""
        message = (
            "[dah<300,30>][dah<60,30>][dah<200,25>][dah<1000,30>][dah<200,23>][dah<400,25>]"
            "[dah<700,18>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def tetris(self, ctx):
        """I am the man who arranges the blocks."""
        message = (
            "[:t 430,500][:t 320,250][:t 350,250][:t 390,500][:t 350,250][:t 330,250][:t 290,500]"
            "[:t 290,250][:t 350,250][:t 430,500]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def soviet(self, ctx):
        """From Russia with love"""
        message = (
            "[lxao<400,23>lxao<800,28>lxao<600,23>lxao<200,25>lxao<1600,27>lxao<800,25>"
            "lxao<600,23>lxao<200,21>lxao<1600,23>][lxao<400,16>][lxao<400,16>][lxao<800,18>]"
            "[lxao<400,18>][lxao<400,20>][lxao<800,21>][lxao<400,21>][lxao<400,23>][lxao<800,25>]"
            "[lxao<400,27>][lxao<400,28>][lxao<800,30>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def allstar(self, ctx):
        """It's all ogre now"""
        message = (
            "[suh<600,19>bah<300,26>diy<200,23>wow<300,23>]uce[tow<300,21>miy<250,19>]"
            "[thuh<250,19>wer<450,24>]urd[ih<100,23>]s[gao<250,23>nah<200,21>]roll[miy<200,19>]"
            "[ay<200,19>][ey<200,26>]int[thuh<200,23>]sharp[eh<200,21>]estool[ih<200,19>]nthuh[sheh<400,16>][eh<300,14>]ed. "
            "[shiy<300,19>][wah<300,19>][lxuh<200,26>][kih<200,23>][kay<300,23>][nah<300,21>][duh<250,21>]uhm"
            "[wih<250,19>][fer<250,19>][fih<450,24>]ing[gur<200,23>][ah<250,23>][ner<200,21>][thuh<200,21>]uhm"
            "[ih<200,19>][thuh<200,19>][shey<400,26>][puh<200,23>]fan[_<50,21>]L[ah<200,19>]ner[for<400,21>][eh<300,14>]ed"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def careless(self, ctx):
        """I have pop pop in the attic"""
        message = (
            "[dah<400,29>dah<200,27>dah<400,22>dah<300,18>dah<500,29>dah<200,27>dah<400,22>dah<400,18>]. "
            "[dah<400,25>dah<200,23>dah<400,18>dah<300,15>dah<500,25>dah<200,23>dah<400,18>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def cena(self, ctx):
        """And his name is!"""
        message = (
            "[bah<300,20>dah<200,22>dah<200,18>dah<600,20>]. "
            "[bah<400,23>dah<200,22>dah<200,18>dah<700,20>]"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def one(self, ctx):
        """We are number one!"""
        message = (
            "[dah<450,18>][dah<150,25>][dah<75,24>][dah<75,25>][dah<75,24>][dah<75,25>]"
            "[dah<150,24>][dah<150,25>][dah<300,21>][dah<600,18>][dah<150,18>][dah<150,21>]"
            "[dah<150,25>][dah<300,26>][dah<300,21>][dah<300,26>][dah<300,28>][w<100,25>]ee"
            "[ar<100,26>][n<100,25>]a[m<100,26>]r[w<100,25>]on"
        )
        await self.speech.say.callback(self.speech, ctx, message=message)

## Main

def load_json(path):
    with open(path, "r") as fd:
        return json.load(fd)


def main():
    ## Todo: Customize the help screen (commands.HelpFormatter), remove tts from it

    ## Init the bot
    bot = commands.Bot(
        command_prefix=commands.when_mentioned_or(ACTIVATION_STRING),
        description=DESCRIPTION
    )
    bot.add_cog(Speech(bot))
    bot.add_cog(SpeechPreset(bot))

    @bot.event
    async def on_ready():
        print("Logged in as {}, {}".format(bot.user.name, bot.user.id))

    ## Blocking execute
    bot.run(load_json(TOKEN_JSON_PATH)[TOKEN_KEY])


if(__name__ == "__main__"):
    main()