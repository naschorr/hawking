import logging
from pathlib import Path

import utilities
from discoverable_module import DiscoverableModule
from module_initialization_struct import ModuleInitializationStruct

from praw import Reddit as PrawReddit

## Config
CONFIG_OPTIONS = utilities.load_module_config(Path(__file__).parent)

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class Reddit(DiscoverableModule):
    def __init__(self, *args, **kwargs):
        client_id = CONFIG_OPTIONS.get('reddit_client_id')
        client_secret = CONFIG_OPTIONS.get('reddit_secret')
        user_agent = self._build_user_agent_string(
            CONFIG_OPTIONS.get('reddit_user_agent_description'),
            CONFIG_OPTIONS.get('reddit_user_agent_contact_name')
        )

        try:
            self._reddit = PrawReddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
            self.successful = True
        except Exception as e:
            logger.error('Unable to register with Reddit', e)
            

    ## Properties

    @property
    def reddit(self):
        return self._reddit

    ## Methods

    def _build_user_agent_string(self, description: str, contact_name: str) -> str:
        if (description.find('Make sure to change this') > -1):
            raise RuntimeWarning('The reddit_user_agent_description property in config.json must be changed!')

        if (description.find('Make sure to change this') > -1):
            raise RuntimeWarning('The reddit_user_agent_contact_name property in config.json must be changed!')

        if (description):
            description.format(version=CONFIG_OPTIONS.get('version', '0.0.1'))

        return "{} (by {})".format(description, contact_name)


def main() -> ModuleInitializationStruct:
    return ModuleInitializationStruct(Reddit, False, use_root_instance=False, use_bot_instance=False)
