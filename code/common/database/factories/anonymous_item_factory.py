from discord import Interaction
from discord.ext.commands import Context

from common.database.models.anonymous_item import AnonymousItem
from common.database.models.detailed_item import DetailedItem
from common.command_management.command_reconstructor import CommandReconstructor
from common.module.module import Module

class AnonymousItemFactory(Module):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.command_reconstructor: CommandReconstructor = kwargs.get('dependencies', {}).get('CommandReconstructor')
        assert (self.command_reconstructor is not None)


    def create(self, data: Interaction | Context, detailed_item: DetailedItem) -> AnonymousItem:
        return AnonymousItem(
            detailed_item.qualified_command_string,
            detailed_item.command_name,
            self.command_reconstructor.reconstruct_command_string(
                data,
                add_parameter_keys=True,
                anonymize_mentions=True
            ),
            detailed_item.is_app_command,
            detailed_item.created_at,
            detailed_item.is_valid
        )
