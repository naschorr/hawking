import logging

from discord import Interaction
from discord.ext.commands import Context

from common.configuration import Configuration
from common.logging import Logging
from common.module.module import Module
from core.message_parser import MessageParser

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class CommandReconstructor(Module):
    ## Could maybe leverage static methods, but I don't really want to rework how the module management system works
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.message_parser: MessageParser = kwargs.get('dependencies', {}).get('MessageParser')
        assert(self.message_parser is not None)


    def _reconstruct_command_from_context(self, context: Context) -> str:
        ## No param values stored in the context now? Names are available, but that's not very useful.
        return f"{context.clean_prefix}{context.command.qualified_name}"


    def _reconstruct_command_from_interaction(self, interaction: Interaction, add_parameter_keys = False, anonymize_mentions = False) -> str:
        ## All interactions refer to slash commands, right?
        prefix = "/"
        name = interaction.command.qualified_name
        parameters = []

        for option in list(interaction.data.get("options", [])):
            flavor = int(option["type"])
            key = option["name"] + ":"
            value = option["value"]

            ## https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-option-type
            if (flavor == 6 or flavor == 8):   ## User or Role
                value = f"<@{value}>"
            elif (flavor == 7): ## Channel
                value = f"<#{value}>"
            elif (flavor == 9): ## Mentionable (how's this different from users or roles? Different format?)
                value = f"<@{value}>"

            parameter = f"{key if add_parameter_keys else ''}{value}"
            parameters.append(parameter)

        command_string = f"{prefix}{name}{(' ' if parameters else '') + (' '.join(parameters))}"

        return self.message_parser.replace_mentions(
            command_string,
            interaction.data,
            hide_mention_formatting=False,
            hide_meta_mentions=False,
            anonymize_mentions=anonymize_mentions
        )


    def reconstruct_command_string(self, data: Context | Interaction, add_parameter_keys = False, anonymize_mentions = False) -> str:
        """Builds an approximation of the string entered by the user to invoke the provided command"""

        if (isinstance(data, Context)):
            return self._reconstruct_command_from_context(data)
        elif (isinstance(data, Interaction)):
            return self._reconstruct_command_from_interaction(data, add_parameter_keys, anonymize_mentions)
        else:
            raise RuntimeError("Unable to reconstruct command string, data isn't of type Context or Interaction")
