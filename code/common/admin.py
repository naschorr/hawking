import inspect

from common import utilities
from common import dynamo_manager
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_struct import ModuleInitializationStruct

from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()


class Admin(DiscoverableCog):
    ## Keys
    ADMINS_KEY = "admins"
    ANNOUNCE_UPDATES_KEY = "announce_updates"

    def __init__(self, hawking, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hawking = hawking
        self.bot = bot
        self.admins = CONFIG_OPTIONS.get(self.ADMINS_KEY, [])
        self.announce_updates = CONFIG_OPTIONS.get(self.ANNOUNCE_UPDATES_KEY, False)

        self.dynamo_db = dynamo_manager.DynamoManager()

    ## Properties

    @property
    def audio_player_cog(self):
        return self.hawking.get_audio_player_cog()

    @property
    def phrases_cog(self):
        return self.hawking.get_phrases_cog()

    ## Methods

    ## Checks if a user is a valid admin
    def is_admin(self, name):
        return (str(name) in self.admins)

    ## Commands

    ## Root command for other admin-only commands
    @commands.group(no_pm=True, hidden=True)
    async def admin(self, ctx):
        """Root command for the admin-only commands"""

        if(ctx.invoked_subcommand is None):
            if(self.is_admin(ctx.message.author)):
                await ctx.send("Missing subcommand.")
                return True
            else:
                await ctx.send("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
                return False

        return False


    ## Tries to reload the preset phrases (admin only)
    @admin.command(no_pm=True)
    async def reload_phrases(self, ctx):
        """Reloads the list of preset clips."""

        ## I don't really like having core modules intertwined with dynamic ones, maybe move the appropriate admin
        ## modules out into their dynamic module and exposing some admin auth function that they check in with before
        ## running the command?
        if(not self.phrases_cog):
            await ctx.send("Sorry <@{}>, but the phrases cog isn't available.".format(ctx.message.author.id))
            return False

        if(not self.is_admin(ctx.message.author)):
            await ctx.send("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            self.dynamo_db.put(dynamo_manager.CommandItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False))
            return False

        count = self.phrases_cog.reload_phrases()

        loaded_clips_string = "Loaded {} phrase{}.".format(count, "s" if count != 1 else "")
        await ctx.send(loaded_clips_string)

        self.dynamo_db.put(dynamo_manager.CommandItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))
        return (count >= 0)


    ## Tries to reload the addon cogs (admin only)
    @admin.command(no_pm=True)
    async def reload_cogs(self, ctx):
        """Reloads the bot's cogs."""

        if(not self.is_admin(ctx.message.author)):
            await ctx.send("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            self.dynamo_db.put(dynamo_manager.CommandItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False))
            return False

        count = self.hawking.module_manager.reload_all()
        total = len(self.hawking.module_manager.modules)

        loaded_cogs_string = "Loaded {} of {} cogs.".format(count, total)
        await ctx.send(loaded_cogs_string)

        self.dynamo_db.put(dynamo_manager.CommandItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))
        return (count >= 0)


    ## Skips the currently playing audio (admin only)
    @admin.command(no_pm=True)
    async def skip(self, ctx):
        """Skips the current audio."""

        if(not self.is_admin(ctx.message.author)):
            logger.debug("Unable to admin skip audio, user: {} is not an admin".format(ctx.message.author.name))
            await ctx.send("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            return False

        await self.audio_player_cog.skip(ctx, force = True)
        return True


    ## Disconnects the bot from their current voice channel
    @admin.command(no_pm=True)
    async def disconnect(self, ctx):
        """ Disconnect from the current voice channel."""

        if(not self.is_admin(ctx.message.author)):
            await ctx.send("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            self.dynamo_db.put(dynamo_manager.CommandItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False))
            return False

        state = self.audio_player_cog.get_server_state(ctx)
        await state.ctx.voice_client.disconnect()

        self.dynamo_db.put(dynamo_manager.CommandItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))
        return True
