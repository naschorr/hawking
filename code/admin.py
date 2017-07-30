import importlib
from collections import OrderedDict

import utilities
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()


class Admin:
    ## Keys
    ADMINS_KEY = "admins"

    def __init__(self, bot, speech_cog_name="Speech", phrases_cog_name="Phrases"):
        self.bot = bot
        self.speech_cog_name = speech_cog_name
        self.phrases_cog_name = phrases_cog_name
        self.admins = CONFIG_OPTIONS.get(self.ADMINS_KEY, [])

        ## These cogs are important, so make sure that they're available
        self.speech_cog = self.bot.get_cog(self.speech_cog_name)
        self.phrases_cog = self.bot.get_cog(self.phrases_cog_name)

        self.modules = OrderedDict()

    ## Methods

    ## Register an arbitrary cog's module, and everything needed to instantiate it
    def register_module(self, module, cls, cog_name=None, *cls_args, **cls_kwargs):
        if(not cog_name):
            cog_name = cog_instance.__class__.__name__

        self.modules[cog_name] = (module, cls, cls_args, cls_kwargs)

        if(not self.bot.get_cog(cog_name)):
            cog_cls = getattr(module, cog_name)
            self.bot.add_cog(cog_cls(*cls_args, **cls_kwargs))

        ## Todo: make this better?
        if(cog_name == self.speech_cog_name):
            self.speech_cog = self.bot.get_cog(self.speech_cog_name)
        elif(cog_name == self.phrases_cog_name):
            self.phrases_cog = self.bot.get_cog(self.phrases_cog_name)


    ## Reloads a module
    def reload_module(self, module):
        try:
            importlib.reload(module)
        except Exception as e:
            print("Error: ({}) reloading module: {}".format(e, module))
            return False
        else:
            return True


    ## Reloads a cog attached to the bot
    def reload_cog(self, cog_name):
        module, cls, cls_args, cls_kwargs = self.modules[cog_name]

        self.bot.remove_cog(cog_name)
        self.reload_module(module)
        cog_cls = getattr(module, cog_name)
        self.bot.add_cog(cog_cls(*cls_args, **cls_kwargs))

        ## Todo: make this better?
        if(cog_name == self.speech_cog_name):
            self.speech_cog = self.bot.get_cog(self.speech_cog_name)
        elif(cog_name == self.phrases_cog_name):
            self.phrases_cog = self.bot.get_cog(self.phrases_cog_name)


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
        await self.speech_cog.say.callback(self.speech_cog, ctx, message=loaded_phrases_string)

        return (count >= 0)


    ## Tries to reload the addon cogs (admin only)
    @admin.command(pass_context=True, no_pm=True)
    async def reload_cogs(self, ctx):
        """Reloads the added cogs."""

        if(not self.is_admin(ctx.message.author)):
            await self.bot.say("<@{}> isn't allowed to do that.".format(ctx.message.author.id))
            return False

        counter = 0
        for cog_name in self.modules:
            try:
                self.reload_cog(cog_name)
            except Exception as e:
                print("Error: {} when reloading cog: {}".format(e, cog_name))
            else:
                counter += 1

        loaded_cogs_string = "Loaded {} cog{}.".format(counter, "s" if counter != 1 else "")
        print(loaded_cogs_string)
        await self.bot.say(loaded_cogs_string)
        await self.speech_cog.say.callback(self.speech_cog, ctx, message=loaded_cogs_string)

        return (counter >= 0)


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
