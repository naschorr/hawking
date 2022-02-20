import os
import logging
import inspect
import boto3
from boto3.dynamodb.conditions import Key

from common import utilities
from .detailed_item import DetailedItem

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class DynamoManager:
    def __init__(self):
        self.enabled = CONFIG_OPTIONS.get('database_enable', False)
        self.credentials_path = CONFIG_OPTIONS.get('database_credentials_file_path')
        self.resource = CONFIG_OPTIONS.get('database_resource', 'dynamodb')
        self.region_name = CONFIG_OPTIONS.get('database_region_name', 'us-east-2')
        self.detailed_table_name = CONFIG_OPTIONS.get('database_detailed_table_name', 'HawkingDetailed')
        self.anonymous_table_name = CONFIG_OPTIONS.get('database_anonymous_table_name', 'HawkingAnonymous')
        self.primary_key = CONFIG_OPTIONS.get('database_primary_key', 'QueryId')
        self.detailed_table_ttl_seconds = CONFIG_OPTIONS.get('database_detailed_table_ttl_seconds', 31536000)

        self.dynamo_db = boto3.resource(self.resource, region_name=self.region_name)
        self.detailed_table = self.dynamo_db.Table(self.detailed_table_name)
        self.anonymous_table = self.dynamo_db.Table(self.anonymous_table_name)

    ## Properties

    @property
    def credentials_path(self):
        return self._credentials_path


    @credentials_path.setter
    def credentials_path(self, value):
        if (not value):
            self._credentials_path = None
            return

        self._credentials_path = value
        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = self.credentials_path

    ## Methods

    def put(self, dynamo_item: DetailedItem):
        '''
        Handles storing the given dynamo_item representing the audio command, as well as storing the anonymized version
        of the command.
        '''

        if (not self.enabled):
            return None

        detailed_item = dynamo_item.to_json()
        anonymous_item = dynamo_item.to_anonymous_item().to_json()

        try:
            self.anonymous_table.put_item(Item=anonymous_item)
        except Exception as e:
            ## Don't let issues with dynamo tank the bot's functionality
            logger.exception("Exception while performing database put into {}".format(self.detailed_table_name), e)
            return None

        try:
            self.detailed_table.put_item(Item=detailed_item)
        except Exception as e:
            ## Don't let issues with dynamo tank the bot's functionality
            logger.exception("Exception while performing database put into {}".format(self.anonymous_table_name), e)
            return None


    def build_message_context(self, discord_context, valid=True) -> DetailedItem:
        '''
        Builds a DetailedItem from the given discord_context, pulled from the message that invoked the bot
        '''

        # Traverse framestack to find first non-dynamo-manager function, that must be the command that was invoked
        frame_stack = inspect.stack()
        frame_index = 0
        frame_info = frame_stack[frame_index]
        while (__file__ in frame_info.frame.f_code.co_filename and frame_index < len(frame_stack)):
            frame_index += 1
            frame_info = frame_stack[frame_index]

        return DetailedItem(discord_context, discord_context.message.content, frame_info.frame.f_code.co_name, valid)


    def put_message_context(self, discord_context, valid=True):
        '''
        Handles the process of storing a given message in the database. Converts the context into a DetailedItem and an
        AnonymousItem, and puts them into the database
        '''

        detailed_item = self.build_message_context(discord_context, valid)
        self.put(detailed_item)


    def build_multi_user_filter_expression(self, user_ids=[]):
        '''
        Builds a multi user filter expression for querying the database. User ids are OR'd together, so that any
        document matching any part of the filter will be returned.
        '''

        if (len(user_ids) == 0):
            return None
        
        filter_expression = Key('user_id').eq(user_ids[0])
        for user_id in user_ids[1:]:
            filter_expression |= Key('user_id').eq(user_id)

        return filter_expression


    async def get_keys_from_users(self, table, user_ids=[]):
        '''
        Performs a lookup on the supplied table to determine what primary key each user_id corresponds to
        '''

        if (not self.enabled):
            return []

        scan_kwargs = {
            'FilterExpression': self.build_multi_user_filter_expression(user_ids)
        }

        ## Scan through the database looking for all documents where the user that made it matches up with one of the
        ## provided user_ids
        done = False
        start_key = None
        results = []
        while (not done):
            if (start_key):
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = table.scan(**scan_kwargs)
            results.extend(response.get('Items', []))
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None

        return results


    async def batch_delete(self, table, primary_keys=[]):
        '''
        Handles deleting all of the listed primary_keys from the supplied table in a batch operation. Note that this
        only works for tables that only use a primary partition key, if you've got additional keys then this will fail
        out.
        '''

        if (not self.enabled):
            return

        with table.batch_writer() as batch:
            for key in primary_keys:
                key_value = {self.primary_key: key}

                batch.delete_item(
                    Key = key_value
                )
