import logging
from random import choice

from common.command_management.invoked_command import InvokedCommand
from common.command_management.invoked_command_handler import InvokedCommandHandler
from common.logging import Logging
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_container import ModuleInitializationContainer

import discord

## Logging
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class Fortune(DiscoverableCog):
    ## Defaults
    FORTUNES = [
        ## Positive
        "It is certain",
        "It is decidely so",
        "Without a doubt",
        "Yes, definitely",
        "Without a doubt",
        "You may rely on it",
        "As I see it, yes",
        "Most likely",
        "Outlook good",
        "Yep",
        "Signs point to yes",
        ## Neutral
        "Reply hazy, try again",
        "Ask again later",
        "Better not tell you now",
        "Cannot predict now",
        "Concentrate and ask again",
        ## Negative
        "Don't count on it",
        "My reply is no",
        "My sources say no",
        "Outlook not so good",
        "Very doubtful"
    ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.speech_cog = kwargs.get('dependencies', {}).get('Speech')
        assert (self.speech_cog is not None)
        self.invoked_command_handler: InvokedCommandHandler = kwargs.get('dependencies', {}).get('InvokedCommandHandler')
        assert(self.invoked_command_handler is not None)


    @discord.app_commands.command(name="fortune")
    async def fortune_command(self, interaction: discord.Interaction):
        """Tells you your magic 8 ball fortune!"""

        fortune = choice(self.FORTUNES)


        async def callback(invoked_command: InvokedCommand):
            if (invoked_command.successful):
                await self.database_manager.store(interaction)
                await interaction.response.send_message(f"{fortune}.")
            else:
                await self.database_manager.store(interaction, valid=False)
                await interaction.response.send_message(invoked_command.human_readable_error_message, ephemeral=True)


        action = lambda: self.speech_cog.say(fortune, author=interaction.user, ignore_char_limit=True, interaction=interaction)
        await self.invoked_command_handler.invoke_command(interaction, action, ephemeral=False, callback=callback)


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(Fortune, dependencies=["Speech", "InvokedCommandHandler"])
