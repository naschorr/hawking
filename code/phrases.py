from discord.ext import commands

class Phrases:
    def __init__(self, bot, speech_cog_name="Speech"):
        self.bot = bot
        self.speech = self.bot.get_cog(speech_cog_name)


    async def _say_phrase(self, ctx, message):
        await self.speech.say.callback(self.speech, ctx, message=message)


    @commands.command(pass_context=True, no_pm=True)
    async def pizza(self, ctx):
        """Time for some pizza"""
        message = (
            "[:nh]I'm gonna eat a pizza. [:dial67589340] Hi, can i order a pizza?"
            "[:nv]no! [:nh]why? [:nv] cuz you are john madden![:np]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def skeletons(self, ctx):
        """Spooky and scary"""
        message = (
            "[spuh<300,19>kiy<300,19>skeh<300,18>riy<300,18>skeh<300,11>lleh<175,14>tih<200,11>ns]\n"
            "[seh<300,11>nd][shih<100,19>ver<500,19>sdaw<300,18>nyur<300,18>spay<300,11>n]\n"
            "[shriy<300,19>kiy<300,19>ng][skow<300,18>swih<300,18>ll]\n"
            "[shah<300,11>kyur<300,14>sow<300,11>ll]\n"
            "[siy<300,14>llyur<300,16>duh<300,13>mtuh<300,14>nay<300,11>t]\n"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def taps(self, ctx):
        """o7"""
        message = (
            "[pr<600,18>][pr<200,18>][pr<1800,23>_>pr<600,18>][pr<300,23>][pr<1800,27>]\n"
            "[pr<600,18>][pr<300,23>][pr<1200,27>][pr<600,18>][pr<300,23>][pr<1200,27>]\n"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def birthday(self, ctx):
        """A very special day"""
        message = (
            "[hxae<300,10>piy<300,10>brr<600,12>th<100>dey<600,10>tuw<600,15>yu<1200,14>_<120>]\n"
            "[hxae<300,10>piy<300,10>brr<600,12>th<100>dey<600,10>tuw<600,17>yu<1200,15>_<120>]\n"
            "[hxae<300,10>piy<300,10>brr<600,22>th<100>dey<600,19>"
            "jh<100>aa<600,15>n<100>m<100>ae<600,14>d<50>dih<600,12>n]\n"
            "[hxae<300,20>piy<300,20>brr<600,19>th<100>dey<600,15>tuw<600,17>yu<1200,15>_<120>]\n"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def mamamia(self, ctx):
        """Could you handle that, dear?"""
        message = (
            "mamma mia, poppa pia, baby got the dy[aa<999,999>]reeeeeeeeeaaaaaaaaaa"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def imperial(self, ctx):
        """Marching along"""
        message = (
            "[dah<600,20>][dah<600,20>][dah<600,20>][dah<500,16>][dah<130,23>][dah<600,20>]"
            "[dah<500,16>]\n"
            "[dah<130,23>][dah<600,20>]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def daisy(self, ctx):
        """I'm afraid I can't do that."""
        message = (
            "[dey<600,24>ziy<600,21>dey<600,17>ziy<600,12>gih<200,14>vmiy<200,16>yurr<200,17>"
            "ah<400,14>nsrr<200,17>duw<1200,12>]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def ateam(self, ctx):
        """I love it when a plan comes together!"""
        message = (
            "[dah<300,30>][dah<60,30>][dah<200,25>][dah<1000,30>][dah<200,23>][dah<400,25>]"
            "[dah<700,18>]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def tetris(self, ctx):
        """I am the man who arranges the blocks."""
        message = (
            "[:t 430,500][:t 320,250][:t 350,250][:t 390,500][:t 350,250][:t 330,250][:t 290,500]"
            "[:t 290,250][:t 350,250][:t 430,500]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def soviet(self, ctx):
        """From Russia with love"""
        message = (
            "[lxao<400,23>lxao<800,28>lxao<600,23>lxao<200,25>lxao<1600,27>lxao<800,25>"
            "lxao<600,23>lxao<200,21>lxao<1600,23>][lxao<400,16>][lxao<400,16>][lxao<800,18>]"
            "[lxao<400,18>][lxao<400,20>][lxao<800,21>][lxao<400,21>][lxao<400,23>][lxao<800,25>]"
            "[lxao<400,27>][lxao<400,28>][lxao<800,30>]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def allstar(self, ctx):
        """It's all ogre now"""
        message = (
            "[suh<600,19>bah<300,26>diy<200,23>wow<300,23>]uce[tow<300,21>miy<250,19>]"
            "[thuh<250,19>wer<450,24>]urd[ih<100,23>]s[gao<250,23>nah<200,21>]roll[miy<200,19>]"
            "[ay<200,19>][ey<200,26>]int[thuh<200,23>]sharp[eh<200,21>]estool[ih<200,19>]nthuh"
            "[sheh<400,16>][eh<300,14>]ed\n"
            "[shiy<300,19>][wah<300,19>][lxuh<200,26>][kih<200,23>][kay<300,23>][nah<300,21>]"
            "[duh<250,21>]uhm[wih<250,19>][fer<250,19>][fih<450,24>]ing[gur<200,23>][ah<250,23>]"
            "[ner<200,21>][thuh<200,21>]uhm[ih<200,19>][thuh<200,19>][shey<400,26>][puh<200,23>]"
            "fan[_<50,21>]L[ah<200,19>]ner[for<400,21>][eh<300,14>]ed"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def careless(self, ctx):
        """I have pop pop in the attic"""
        message = (
            "[dah<400,29>dah<200,27>dah<400,22>dah<300,18>dah<500,29>dah<200,27>dah<400,22>dah<400,18>]\n"
            "[dah<400,25>dah<200,23>dah<400,18>dah<300,15>dah<500,25>dah<200,23>dah<400,18>]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def cena(self, ctx):
        """And his name is..."""
        message = (
            "[bah<300,20>dah<200,22>dah<200,18>dah<600,20>]\n"
            "[bah<400,23>dah<200,22>dah<200,18>dah<700,20>]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def one(self, ctx):
        """We are number one!"""
        message = (
            "[dah<450,18>][dah<150,25>][dah<75,24>][dah<75,25>][dah<75,24>][dah<75,25>]"
            "[dah<150,24>][dah<150,25>][dah<300,21>][dah<600,18>][dah<150,18>][dah<150,21>]"
            "[dah<150,25>][dah<300,26>][dah<300,21>][dah<300,26>][dah<300,28>][w<100,25>]ee"
            "[ar<100,26>][n<100,25>]a[m<100,26>]r[w<100,25>]on"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def whalers(self, ctx):
        """On the moon!"""
        message = (
            "[_<1,13>]we're[_<1,18>]whalers[_<1,17>]on[_<1,18>]the[_<1,20>]moon\n"
            "[_<400,13>]we[_<1,20>]carry[_<1,18>]a[_<1,20>]har[_<1,22>]poon\n"
            "[_<1,22>]but there[_<1,23>]aint no[_<1,15>]whales[_<1,23>]so we[_<1,22>]tell "
            "tall[_<1,18>]tales and[_<1,20>]sing our[_<1,18>]whale[_<1,17>]ing[_<1,18>]tune"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def madden(self, ctx):
        """Lord and saviour"""
        message = (
            "[ey<900,24>iyuw<450,27>ey<900,34>iyuw<450,32>jhah<900,27>nmae<225,25>ae<225,24>"
            "deh<1350,22>n]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def pirate(self, ctx):
        """That's what you are"""
        message = (
            "[yxar<500,25>hxar<500,25>fih<150,27>del<150,24>diy<150,22>diy<500,20>]"
        )
        await self._say_phrase(ctx, message)


    @commands.command(pass_context=True, no_pm=True)
    async def snake(self, ctx):
        """!"""
        message = (
            "snake? Snayke! SNAAAAAKEE!"
        )
        await self._say_phrase(ctx, message)