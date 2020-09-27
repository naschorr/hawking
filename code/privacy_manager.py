import os
import pathlib
import stat
import logging

import utilities

from discord.user import User
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class PrivacyManager(commands.Cog):

    def __init__(self, hawking, bot):
        self.hawking = hawking
        self.bot = bot

        self.delete_request_queue_file_path = CONFIG_OPTIONS.get('delete_request_queue_file_path')
        if (not self.delete_request_queue_file_path):
            self.delete_request_queue_file_path = os.sep.join([utilities.get_root_path(), 'privacy', 'delete_requests'])

        ## Make sure the file containing all delete requests is accessible.
        if (not self.is_delete_request_queue_file_accessible()):
            message = "Unable to access delete request queue file at: '{}'. Make sure that it exists and has r/w permissions applied to it".format(self.delete_request_queue_file_path)

            logger.error(message)
            raise RuntimeError(message)

        ## Keep a copy of all user ids that should be deleted in memory, so the actual file can't get spammed by repeats.
        self.queued_user_ids = self.get_all_queued_delete_request_ids()

    ## Methods

    def is_delete_request_queue_file_accessible(self) -> bool:
        '''Ensures that the file that holds the delete requests is accessible'''

        path = pathlib.Path(self.delete_request_queue_file_path)

        if (path.is_file()):
            if (    os.access(path, os.R_OK) and
                    os.access(path, os.W_OK)):
                return True
            else:
                try:
                    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
                    return True
                except Exception:
                    return False
        else:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)    ## Basically mkdir -p on the parent directory
                path.touch(0o644, exist_ok=True)    ## u+rw, go+r
                return True
            except Exception as e:
                return False


    def get_all_queued_delete_request_ids(self) -> set:
        '''Retrieves all delete request ids from the file, and returns them all in a set'''

        queued_user_ids = None

        with open(self.delete_request_queue_file_path, 'r+') as fd:
            queued_user_ids = set([int(line.rstrip()) for line in fd.readlines()])

        return queued_user_ids


    ## Stores's a user's id in a file, which while be used in a batched request to delete their data from the remote DB
    def store_user_id_for_batch_delete(self, user_id):
        '''
        Stores's a user's id in a file, which while be used in a batched request to delete their data from the remote DB
        '''

        self.queued_user_ids.add(user_id)

        with open(self.delete_request_queue_file_path, 'a+') as fd:
            fd.write(str(user_id) + '\n')

    ## Commands

    @commands.command(no_pm=True, hidden=True)
    async def delete_my_data(self, ctx):
        '''
        Initiates a request to delete all of your user data from Hawking's logs.
        All delete requests are queued up and performed in a batch every Monday.
        '''

        self.dynamo_db.put(dynamo_helper.DynamoItem(
            ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))

        user = ctx.message.author
        if (user.id in self.queued_user_ids):
            await user.send("Hey <@{}>, it looks like you've already requested that your data be deleted. That'll automagically happen next Monday, so sit tight and it'll happen before you know it!".format(user.id))
            return

        self.store_user_id_for_batch_delete(user.id)

        await user.send("Hey <@{}>, your delete request has been received, and it'll happen automagically next Monday. Thanks for using Hawking!".format(user.id))
