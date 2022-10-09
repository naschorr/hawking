import logging

from hawking import Hawking
from common.configuration import Configuration
from common.database.database_manager import DatabaseManager
from common.logging import Logging
from common.module.module import Cog
from common.module.module_initialization_container import ModuleInitializationContainer

from discord.ext import commands
from discord.ext.commands import Bot, Context, errors

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class AdminCog(Cog):
    ## Keys
    ADMINS_KEY = "admins"
    ANNOUNCE_UPDATES_KEY = "announce_updates"

    def __init__(self, hawking: Hawking, bot: Bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)

        self.hawking = hawking
        self.bot = bot

        self.database_manager: DatabaseManager = kwargs.get('dependencies', {}).get('DatabaseManager')
        assert (self.database_manager is not None)

        self.admins = CONFIG_OPTIONS.get(self.ADMINS_KEY, [])
        self.announce_updates = CONFIG_OPTIONS.get(self.ANNOUNCE_UPDATES_KEY, False)

    ## Commands

    @commands.group(hidden=True)
    @commands.is_owner()
    async def admin(self, ctx: Context):
        """Root command for the admin-only commands"""

        if(ctx.invoked_subcommand is None):
            await ctx.message.reply("Missing subcommand")


    @admin.command()
    async def sync_local(self, ctx: Context):
        """Syncs bot command tree to the current guild"""

        await self.database_manager.store(ctx)

        ## Sync example: https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f?permalink_comment_id=4121434#gistcomment-4121434
        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)

        await ctx.message.reply(f"Synced {len(synced)} commands locally.")


    @admin.command()
    async def sync_global(self, ctx: Context):
        """Syncs bot command tree to the all guilds"""

        await self.database_manager.store(ctx)

        synced = await self.bot.tree.sync()

        await ctx.message.reply(f"Synced {len(synced)} commands globally.")


    @admin.command()
    async def clear_local(self, ctx: Context):
        """Removed all bot commands from the current guild"""

        await self.database_manager.store(ctx)

        ## todo: No global clear method? Is that as designed and normal syncing is fine?
        self.bot.tree.clear_commands(guild=ctx.guild)
        await self.bot.tree.sync()

        await ctx.message.reply("Removed all commands locally.")


    @admin.command(no_pm=True)
    async def reload_modules(self, ctx: Context):
        """Reloads the bot's modules"""

        await self.database_manager.store(ctx)

        count = await self.hawking.module_manager.reload_registered_modules()
        total = len(self.hawking.module_manager.modules)

        loaded_modules_string = f"Loaded {count} of {total} modules/cogs. Consider syncing commands if anything has changed."
        await ctx.reply(loaded_modules_string)

        return (count >= 0)


    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        if (isinstance(error, errors.NotOwner)):
            await self.database_manager.store(ctx, valid=False)
            await ctx.message.reply("Sorry, this command is only available to the bot's owner (and not the server owner).")
            return

        return await super().cog_command_error(ctx, error)

