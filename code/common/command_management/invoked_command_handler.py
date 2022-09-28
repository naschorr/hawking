import asyncio
import logging
from typing import Callable

from common.configuration import Configuration
from common.command_management.invoked_command import InvokedCommand
from common.logging import Logging
from common.module.module import Module

from discord import Interaction, Member

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class InvokedCommandHandler(Module):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    ## Methods

    def get_first_mention(self, interaction: Interaction) -> Member | None:
        mention = None

        members = interaction.data.get("resolved", {}).get("members", {})
        if (len(members.items()) == 0):
            return None

        ## Note that popitem will return the "first" item in the resolved members dict, which isn't necessarily the
        ## first user mentioned
        potential_mention = members.popitem()
        if (potential_mention is not None):
            ## popitem returns a tuple of the mapping, so make sure we're working with the actual value, and not the key-value pair
            potential_mention = potential_mention[1]
            mention = Member(data=potential_mention, guild=interaction.guild, state=interaction._state)

        return mention


    def get_command_string_from_interaction(self, interaction: Interaction) -> str:
        command_name = interaction.command.name ## todo: Is this the name invoked by the user, or the actual name of the method?

        options = " ".join([option.get("value") for option in interaction.data.get("options", [{}]) if option.get("value") is not None])  ## todo: any other flavors of argument?
        if (options != ""):
            options = f" {options}" ## Prepend a spacer if necessary so everything has some room to breathe (see return below)

        ## These should always be slash commands, so the explicit '/' character is fine
        return f"/{command_name}{options}"


    async def handle_deferred_command(
            self,
            interaction: Interaction,
            action: Callable[..., InvokedCommand],
            ephemeral: bool = True,
            callback: Callable[[InvokedCommand], None] = None
    ):
        '''Handles user feedback when running a deferred command'''

        ## Acknowledge the command, and start the thinking state
        command_string = self.get_command_string_from_interaction(interaction)
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)

        ## Act upon the command, giving human readable feedback if any errors pop up
        try:
            invoked_command = await action()

            ## Let the client handle followup feedback if desired
            if(callback is not None):
                if(asyncio.iscoroutinefunction(callback)):
                    await callback(invoked_command)
                else:
                    callback(invoked_command)
                return

            ## Otherwise provide some basic feedback, and (implicitly) clear the thinking state
            if (invoked_command.successful):
                await interaction.followup.send(f"<@{interaction.user.id}> used **{command_string}**")
            elif (invoked_command.human_readable_error_message is not None):
                await interaction.followup.send(invoked_command.human_readable_error_message)
            elif (invoked_command.error is not None):
                raise invoked_command.error
            else:
                raise RuntimeError("Unspecified error during command handling")

        except Exception as e:
            LOGGER.error("Unspecified error during command handling", e)
            await interaction.followup.send(
                f"I'm sorry <@{interaction.user.id}>, I'm afraid I can't do that.\n" +
                f"Something went wrong, and I couldn't complete the **{command_string}** command.",
                ephemeral=True
            )