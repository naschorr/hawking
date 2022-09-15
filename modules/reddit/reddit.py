import logging
from pathlib import Path

from praw import Reddit as PrawReddit

from common.configuration import Configuration
from common.exceptions import ModuleLoadException
from common.logging import Logging
from common.module.discoverable_module import DiscoverableModule
from common.module.module_initialization_container import ModuleInitializationContainer


## Config & logging
CONFIG_OPTIONS = Configuration.load_config(Path(__file__).parent)
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class Reddit(DiscoverableModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        client_id = CONFIG_OPTIONS.get('reddit_client_id')
        client_secret = CONFIG_OPTIONS.get('reddit_secret')

        ## Is there a better way?
        if (client_id.find('goes here') > -1):
            raise ModuleLoadException('The \'reddit_client_id\' property in config.json must be changed!')
        if (client_secret.find('goes here') > -1):
            raise ModuleLoadException('The \'reddit_secret\' property in config.json must be changed!')

        try:
            user_agent = self._build_user_agent_string(
                CONFIG_OPTIONS.get('reddit_user_agent_platform'),
                CONFIG_OPTIONS.get('reddit_user_agent_app_id'),
                CONFIG_OPTIONS.get('reddit_user_agent_contact_name')
            )
        except RuntimeError as e:
            raise ModuleLoadException("Unable to build user_agent string for Reddit", e)

        try:
            self._reddit = PrawReddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False   ## This infrequently polls Reddit, so moving to asyncpraw isn't necessary
            )
            self.successful = True
        except Exception as e:
            raise ModuleLoadException('Unable to register with Reddit', e)

    ## Properties

    @property
    def reddit(self):
        return self._reddit

    ## Methods

    def _build_user_agent_string(self, platform: str, app_id: str, contact_name: str) -> str:
        ## Again, surely there's a better way!
        if (platform.find('Make sure to change this') > -1):
            raise RuntimeError('The \'reddit_user_agent_platform\' property in config.json must be changed!')
        if (app_id.find('Make sure to change this') > -1):
            raise RuntimeError('The \'reddit_user_agent_app_id\' property in config.json must be changed!')
        if (contact_name.find('Make sure to change this') > -1):
            raise RuntimeError('The \'reddit_user_agent_contact_name\' property in config.json must be changed!')

        version = CONFIG_OPTIONS.get('version', "1.0.0")

        return "{platform}:{app_id}:{version} (by {contact_name})".format(
            platform=platform, app_id=app_id, version=version, contact_name=contact_name
        )


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(Reddit)
