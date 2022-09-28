import inspect
import logging

from hawking import Hawking
from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.module.module import Cog
from common.module.module_initialization_container import ModuleInitializationContainer

from discord.ext import commands
from discord.ext.commands import Context, errors

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class Admin(Cog):
    ## Keys
    ADMINS_KEY = "admins"
    ANNOUNCE_UPDATES_KEY = "announce_updates"

    def __init__(self, hawking: Hawking, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hawking = hawking
        self.bot = bot

        self.admins = CONFIG_OPTIONS.get(self.ADMINS_KEY, [])
        self.announce_updates = CONFIG_OPTIONS.get(self.ANNOUNCE_UPDATES_KEY, False)

        self.dynamo_db = dynamo_manager.DynamoManager()

    ## Methods

    ## Checks if a user is a valid admin
    def is_admin(self, name):
        return (str(name) in self.admins)

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

        ## Sync example: https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f?permalink_comment_id=4121434#gistcomment-4121434
        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)

        await ctx.message.reply(f"Synced {len(synced)} commands locally.")


    @admin.command()
    async def sync_global(self, ctx: Context):
        """Syncs bot command tree to the all guilds"""

        ## Sync example: https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f?permalink_comment_id=4121434#gistcomment-4121434
        synced = await self.bot.tree.sync()

        await ctx.message.reply(f"Synced {len(synced)} commands globally.")


    @admin.command()
    async def clear_global(self, ctx: Context):
        """Removed all bot commands from all guilds"""

        ## Sync example: https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f?permalink_comment_id=4121434#gistcomment-4121434
        self.bot.tree.clear_commands()
        await self.bot.tree.sync()

        await ctx.message.reply("Removed all commands globally.")


    @admin.command(no_pm=True)
    async def reload_modules(self, ctx: Context):
        """Reloads the bot's modules"""

        if(not self.is_admin(ctx.message.author)):
            LOGGER.debug("Unable to admin reload modules, user: {} is not an admin".format(ctx.message.author.name))
            await ctx.send("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            self.dynamo_db.put_message_context(ctx, False)

            return False

        count = self.hawking.module_manager.reload_registered_modules()
        total = len(self.hawking.module_manager.modules)

        loaded_modules_string = "Loaded {} of {} modules/cogs.".format(count, total)
        await ctx.send(loaded_modules_string)
        self.dynamo_db.put_message_context(ctx)

        return (count >= 0)


    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        if (isinstance(error, errors.NotOwner)):
            await ctx.message.reply("Sorry, this command is only available to the bot's owner (and not the server owner).")
            return

        return await super().cog_command_error(ctx, error)

