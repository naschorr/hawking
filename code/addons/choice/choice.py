import logging
from random import choice

from hawking.modules.speech.speech_cog import SpeechCog
from hawking.core.services.command_management.invoked_command import InvokedCommand
from hawking.core.services.command_management.invoked_command_handler import InvokedCommandHandler
from hawking.core.services.database.database_manager import DatabaseManager
from hawking.core.services.logging.logging_service import Logging
from hawking.core.services.module_manager.discoverable_module import DiscoverableCog
from hawking.core.services.module_manager.module_initialization_container import ModuleInitializationContainer

import discord
from discord.ext.commands import Bot


class Choice(DiscoverableCog):
    ## Defaults
    SELECTION_STRINGS = [
        "I choose:",
        "Choosy moms choose:",
        "I'm not too sure, let's just pick this one:",
        "Let's go with this:",
        "How about this one:",
        "This one's good enough:"
    ]


    def __init__(self, config, bot: Bot, **kwargs):
        super().__init__(config, bot, **kwargs)

        self.config = config
        self.logger = Logging.initialize_logging(logging.getLogger(__name__))

        self.speech_cog: SpeechCog = kwargs.get('dependencies', {}).get('SpeechCog')
        assert (self.speech_cog is not None)
        self.invoked_command_handler: InvokedCommandHandler = kwargs.get('dependencies', {}).get('InvokedCommandHandler')
        assert(self.invoked_command_handler is not None)
        self.database_manager: DatabaseManager = kwargs.get('dependencies', {}).get('DatabaseManager')
        assert (self.database_manager is not None)


    @discord.app_commands.command(name="choice")
    @discord.app_commands.describe(options="Comma-separated list of options to choose from")
    async def choice_command(self, interaction: discord.Interaction, options: str):
        """Chooses one of the provided options"""

        selection_string = choice(self.SELECTION_STRINGS)

        parsed_options = [option.strip() for option in options.split(",")]
        if len(parsed_options) <= 1:
            await self.database_manager.store(interaction, valid=False)
            await interaction.response.send_message(f"No valid option provided in: `{options}`.\nPlease split options with commas, like so: `red, blue, green`", ephemeral=True)
            return

        chosen_option = choice(parsed_options)
        choice_text = f"{selection_string} {chosen_option}"

        async def callback(invoked_command: InvokedCommand):
            if (invoked_command.successful):
                await self.database_manager.store(interaction)
                await interaction.response.send_message(choice_text)
            else:
                await self.database_manager.store(interaction, valid=False)
                await interaction.response.send_message(invoked_command.human_readable_error_message, ephemeral=True)


        action = lambda: self.speech_cog.say(
            text=choice_text,
            author=interaction.user,
            ignore_char_limit=True,
            interaction=interaction
        )
        await self.invoked_command_handler.invoke_command(interaction, action, ephemeral=False, callback=callback)


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(Choice, dependencies=["SpeechCog", "InvokedCommandHandler", "DatabaseManager"])
