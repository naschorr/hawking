from calendar import day_name
import os
import stat
import logging
import asyncio
import dateutil
import datetime
import json
import time
from pathlib import Path

from common import utilities
from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.module.module import Cog
from common.ui.embed_factory import EmbedFactory

import discord
from discord import app_commands, Interaction

## Config & logging
CONFIG_OPTIONS = Configuration.load_config()
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class PrivacyManager(Cog):

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        self.embed_factory: EmbedFactory = kwargs.get('dependencies', {}).get('EmbedFactory')
        assert(self.embed_factory is not None)

        self.name = CONFIG_OPTIONS.get("name", "the bot").capitalize()
        self.repo_url = CONFIG_OPTIONS.get("bot_repo_url")
        self.privacy_policy_url = CONFIG_OPTIONS.get('privacy_policy_url')
        self.delete_request_scheduled_weekday = int(CONFIG_OPTIONS.get('delete_request_weekday_to_process', 0))
        self._delete_request_scheduled_weekday_name = utilities.get_weekday_name_from_day_of_week(self.delete_request_scheduled_weekday)
        self.delete_request_scheduled_time = dateutil.parser.parse(CONFIG_OPTIONS.get('delete_request_time_to_process', "T00:00:00Z"))

        ## Build the filepaths for the various tracking files
        delete_request_queue_file_path = CONFIG_OPTIONS.get('delete_request_queue_file_path')
        if (delete_request_queue_file_path):
            self.delete_request_queue_file_path = Path(delete_request_queue_file_path)
        else:
            self.delete_request_queue_file_path = Path.joinpath(utilities.get_root_path(), 'privacy', 'delete_requests.txt')

        delete_request_meta_file_path = CONFIG_OPTIONS.get('delete_request_meta_file_path')
        if (delete_request_meta_file_path):
            self.delete_request_meta_file_path = Path(delete_request_meta_file_path)
        else:
            self.delete_request_meta_file_path = Path.joinpath(utilities.get_root_path(), 'privacy', 'meta.json')

        ## Make sure the file containing all delete requests is accessible.
        if (not self.is_file_accessible(self.delete_request_queue_file_path)):
            message = "Unable to access delete request queue file at: '{}'. Make sure that it exists and has r/w permissions applied to it".format(self.delete_request_queue_file_path)

            LOGGER.error(message)
            raise RuntimeError(message)

        ## Make sure the file containing the delete request metadata is accessible.
        if (not self.is_file_accessible(self.delete_request_meta_file_path)):
            message = "Unable to access delete request queue file at: '{}'. Make sure that it exists and has r/w permissions applied to it".format(self.delete_request_meta_file_path)

            LOGGER.error(message)
            raise RuntimeError(message)

        ## Make sure there's a dynamo manager available for database operations
        self.dynamo_db = dynamo_manager.DynamoManager()

        ## Keep a copy of all user ids that should be deleted in memory, so the actual file can't get spammed by repeats.
        self.queued_user_ids = self.get_all_queued_delete_request_ids()

        ## Load the delete request metadata to know when deletion operations last happened
        try:
            self.metadata = utilities.load_json(self.delete_request_meta_file_path)
        except json.decoder.JSONDecodeError:
            self.metadata = {}

        ## Perform or prepare the deletion process
        seconds_until_process_delete_request = self.get_seconds_until_process_delete_request_queue_is_due()
        if (seconds_until_process_delete_request <= 0):
            asyncio.run(self.process_delete_request_queue())
        else:
            asyncio.run(self.schedule_process_delete_request_queue(seconds_until_process_delete_request))

        ## Add the commands
        self.bot.tree.add_command(discord.app_commands.Command(
            name="delete_my_data",
            description=self.delete_my_data_command.__doc__,
            callback=self.delete_my_data_command
        ))

        # Don't add a privacy policy link if there isn't a URL to link to
        if (self.privacy_policy_url):
            self.bot.tree.add_command(discord.app_commands.Command(
                name="privacy_policy",
                description=self.privacy_policy_command.__doc__,
                callback=self.privacy_policy_command
            ))

    ## Methods

    def is_file_accessible(self, file_path: Path) -> bool:
        """Ensures that the file that holds the delete requests is accessible"""

        if (file_path.is_file()):
            if (    os.access(file_path, os.R_OK) and
                    os.access(file_path, os.W_OK)):
                return True
            else:
                try:
                    os.chmod(file_path, stat.S_IREAD | stat.S_IWRITE)
                    return True
                except Exception:
                    return False
        else:
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)    ## Basically mkdir -p on the parent directory
                file_path.touch(0o644, exist_ok=True)    ## u+rw, go+r
                return True
            except Exception as e:
                return False


    def get_all_queued_delete_request_ids(self) -> set:
        """Retrieves all delete request ids from the file, and returns them all in a set"""

        queued_user_ids = None

        with open(self.delete_request_queue_file_path, 'r+') as fd:
            queued_user_ids = set([int(line.rstrip()) for line in fd.readlines()])

        return queued_user_ids


    def empty_queued_delete_request_file(self):
        open(self.delete_request_queue_file_path, 'w').close()


    ## Stores's a user's id in a file, which while be used in a batched request to delete their data from the remote DB
    async def store_user_id_for_batch_delete(self, user_id):
        """
        Stores's a user's id in a file, which while be used in a batched request to delete their data from the remote DB
        """

        self.queued_user_ids.add(user_id)

        user_id_written = False
        while (not user_id_written):
            try:
                with open(self.delete_request_queue_file_path, 'a+') as fd:
                    fd.write(str(user_id) + '\n')
                user_id_written = True
            except IOError as e:
                LOGGER.exception(f"Unable to write id {user_id} to file at {self.delete_request_queue_file_path}.", e)
                ## Give the file some time to close
                await asyncio.sleep(1);

        return user_id_written


    def update_last_process_delete_request_queue_time(self, update_time):
        self.metadata['last_process_time'] = str(update_time)
        utilities.save_json(self.delete_request_meta_file_path, self.metadata)


    async def process_delete_request_queue(self):
        ## Perform the operations on a list, since they're slightly easier to wrangle than sets.
        user_ids = list(self.get_all_queued_delete_request_ids())

        if (not user_ids):
            LOGGER.info("Skipping delete request processing, as queue is empty.")
            return

        LOGGER.info(f"Starting to process {len(user_ids)} delete requests")
        primary_keys_to_delete = list(map(
            lambda item: item[self.dynamo_db.primary_key],
            await self.dynamo_db.get_keys_from_users(self.dynamo_db.detailed_table, user_ids)
        ))

        LOGGER.info(f"Starting to batch delete {len(primary_keys_to_delete)} documents.")
        await self.dynamo_db.batch_delete(self.dynamo_db.detailed_table, primary_keys_to_delete)

        LOGGER.info("Successfully performed batch delete")
        self.queued_user_ids = set()
        self.empty_queued_delete_request_file()

        LOGGER.info("Updating metadata file with time of completion.")
        self.update_last_process_delete_request_queue_time(datetime.datetime.now(datetime.timezone.utc))


    def get_seconds_until_process_delete_request_queue_is_due(self):
        def copy_time_data_into_datetime(source: datetime.datetime, target: datetime.datetime):
            target.replace(hour=source.hour, minute=source.minute, second=source.second, microsecond=0)

        try:
            last_process_time = dateutil.parser.isoparse(self.metadata.get('last_process_time'))
        except Exception:
            ## If there is no last_process_time property, then it likely hasn't been done. So process the queue immediately
            return 0

        now = datetime.datetime.now(datetime.timezone.utc)

        previous_possible_process_time = now - datetime.timedelta(days=(self.delete_request_scheduled_weekday - now.weekday()) % 7)
        copy_time_data_into_datetime(self.delete_request_scheduled_time, previous_possible_process_time)

        ## Check if it's been more than a week. Otherwise, get the time until the next queue processing should happen
        if (last_process_time.timestamp() < previous_possible_process_time.timestamp()):
            return 0
        else:
            next_possible_process_time = now + datetime.timedelta(days=(self.delete_request_scheduled_weekday - now.weekday()) % 7)
            copy_time_data_into_datetime(self.delete_request_scheduled_time, next_possible_process_time)

            return int(next_possible_process_time.timestamp() - last_process_time.timestamp())


    async def schedule_process_delete_request_queue(self, seconds_to_wait):
        await asyncio.sleep(seconds_to_wait)
        await self.process_delete_request_queue()

    ## Commands

    async def privacy_policy_command(self, interaction: Interaction):
        """Gives a link to the privacy policy"""

        # self.dynamo_db.put_message_context(ctx)

        embed = self.embed_factory.create(
            title="Privacy Policy",
            description=f"{self.name} takes your data seriously.\nTake a look at {self.name}'s [privacy policy]({self.privacy_policy_url}) to learn more.",
            url=self.privacy_policy_url
        )

        view = discord.ui.View()

        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="View the Privacy Policy",
            url=self.privacy_policy_url
        ))

        if (self.repo_url is not None):
            view.add_item(discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Visit Hawking on GitHub",
                url=self.repo_url
            ))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    async def delete_my_data_command(self, interaction: Interaction):
        """Initiates a request to delete all of your user data from the bot's logs."""

        # self.dynamo_db.put_message_context(ctx)

        user_id = interaction.user.id
        if (user_id in self.queued_user_ids):
            await interaction.response.send_message(
                f"Hey <@{user_id}>, it looks like you've already requested that your data be deleted. That'll automagically happen next {self._delete_request_scheduled_weekday_name}, so sit tight and it'll happen before you know it!",
                ephemeral=True
            )
            return

        await self.store_user_id_for_batch_delete(user_id)

        await interaction.response.send_message(
            f"Hey <@{user_id}>, your delete request has been received, and it'll happen automagically next {self._delete_request_scheduled_weekday_name}.",
            ephemeral=True
        )
