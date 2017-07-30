import utilities
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()


class Admin:
    ## Keys
    ADMINS_KEY = "admins"
    ANNOUNCE_UPDATES_KEY = "announce_updates"

    def __init__(self, hawking, bot):
        self.hawking = hawking
        self.bot = bot
        self.admins = CONFIG_OPTIONS.get(self.ADMINS_KEY, [])
        self.announce_updates = CONFIG_OPTIONS.get(self.ANNOUNCE_UPDATES_KEY, False)

    ## Properties

    @property
    def speech_cog(self):
        return self.hawking.get_speech_cog()

    @property
    def phrases_cog(self):
        return self.hawking.get_phrases_cog()

    ## Methods

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
    async def reload_phrases(self, ctx):
        """Reloads the list of preset phrases."""

        if(not self.is_admin(ctx.message.author)):
            await self.bot.say("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            return False

        count = self.phrases_cog.reload_phrases()
        loaded_phrases_string = "Loaded {} phrase{}.".format(count, "s" if count != 1 else "")
        await self.bot.say(loaded_phrases_string)
        if(self.announce_updates):
            await self.speech_cog.say.callback(self.speech_cog, ctx, message=loaded_phrases_string)

        return (count >= 0)


    ## Tries to reload the addon cogs (admin only)
    @admin.command(pass_context=True, no_pm=True)
    async def reload_cogs(self, ctx):
        """Reloads the bot's cogs."""

        if(not self.is_admin(ctx.message.author)):
            await self.bot.say("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            return False

        count = self.hawking.module_manager.reload_all()
        loaded_cogs_string = "Loaded {} cog{}.".format(count, "s" if count != 1 else "")
        await self.bot.say(loaded_cogs_string)
        if(self.announce_updates):
            await self.speech_cog.say.callback(self.speech_cog, ctx, message=loaded_cogs_string)

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
