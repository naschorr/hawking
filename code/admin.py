import utilities
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()


class Admin:
    ## Keys
    ADMINS_KEY = "admins"

    def __init__(self, bot, speech_cog_name="Speech", phrases_cog_name="Phrases"):
        self.bot = bot
        self.speech_cog = self.bot.get_cog(speech_cog_name)
        self.phrases_cog = self.bot.get_cog(phrases_cog_name)
        self.admins = CONFIG_OPTIONS.get(self.ADMINS_KEY, [])


    ## Checks if a user is a valid admin
    def is_admin(self, name):
        return (str(name) in self.admins)

    ## Commands

    ## Root command for other admin-only commands
    @commands.group(pass_context=True, no_pm=True, hidden=True)
    async def admin(self, ctx):
        """Root command for the admin-only commands"""
    
        if(ctx.invoked_subcommand is None):
            if(self.is_admin(ctx.message.author)):
                await self.bot.say("Missing subcommand.".format(ctx.message.author.id))
                return True
            else:
                await self.bot.say("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
                return False

        return False


    ## Tries to reload the preset phrases (admin only)
    @admin.command(pass_context=True, no_pm=True)
    async def reload(self, ctx):
        """Reloads the list of preset phrases."""

        if(not self.is_admin(ctx.message.author)):
            await self.bot.say("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            return False

        count = self.phrases_cog.reload_phrases()
        await self.bot.say("Loaded {} phrases.".format(count))

        return (count >= 0)


    ## Skips the currently playing speech (admin only)
    @admin.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Skips the current speech."""

        if(not self.is_admin(ctx.message.author)):
            await self.bot.say("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            return False

        state = self.speech_cog.get_speech_state(ctx.message.server)
        if(not state.is_speaking()):
            await self.bot.say("I'm not speaking at the moment.")
            return False

        await self.bot.say("<@{}> has skipped the speech.".format(ctx.message.author.id))
        await state.skip_speech()
        return True
