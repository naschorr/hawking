import os
import base64
import time
import logging
import uuid
import boto3
from boto3.dynamodb.conditions import Key

from common import utilities

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))

class CommandItem:
    def __init__(self, discord_context, query, command, is_valid, error=None):
        self.discord_context = discord_context
        author = self.discord_context.message.author
        channel = self.discord_context.message.channel
        guild = self.discord_context.message.guild

        self.user_id = int(author.id)
        self.user_name = "{}#{}".format(author.name, author.discriminator)
        self.timestamp = int(self.discord_context.message.created_at.timestamp() * 1000)    # float to milliseconds timestamp
        self.channel_id = channel.id
        self.channel_name = channel.name
        self.server_id = guild.id
        self.server_name = guild.name

        self.query = query
        self.command = command
        self.is_valid = is_valid
        ## Milliseconds timestamp to seconds, as AWS TTL only works in seconds increments. Defaults to a year from the timestamp
        self.expires_on = (self.timestamp / 1000) + CONFIG_OPTIONS.get("database_detailed_table_ttl_seconds", 31536000)

        self.primary_key_name = CONFIG_OPTIONS.get("boto_primary_key", "QueryId")
        self.primary_key = self.build_primary_key()

    ## Methods

    def getDict(self):
        output = {
            "user_id": int(self.user_id),
            "user_name": str(self.user_name),
            "timestamp": int(self.timestamp),
            "channel_id": int(self.channel_id),
            "channel_name": str(self.channel_name),
            "server_id": int(self.server_id),
            "server_name": str(self.server_name),
            "query": str(self.query),
            "command": str(self.command),
            "is_valid": bool(self.is_valid),
            "expires_on": int(self.expires_on)
        }

        output[self.primary_key_name] = str(self.primary_key)

        return output


    def build_primary_key(self):
        concatenated = "{}{}".format(self.user_id, self.timestamp)

        return base64.b64encode(bytes(concatenated, "utf-8")).decode("utf-8")


    def to_anonymous_command_item(self):
        return AnonymousCommandItem(self.discord_context, self.command, self.query, self.is_valid)


class AnonymousCommandItem:
    def __init__(self, discord_context, command, query, is_valid):
        self.timestamp = int(discord_context.message.created_at.timestamp() * 1000)
        self.command = command
        self.query = query
        self.is_valid = is_valid

        self.primary_key_name = CONFIG_OPTIONS.get("boto_primary_key", "QueryId")
        self.primary_key = self.build_primary_key()

    ## Methods

    def getDict(self):
        output = {
            "timestamp": int(self.timestamp),
            "command": str(self.command),
            "query": str(self.query),
            "is_valid": str(self.is_valid)
        }

        output[self.primary_key_name] = str(self.primary_key)

        return output


    def build_primary_key(self):
        ## Use a UUID because we can't really guarantee that there won't be collisions with the existing data (however unlikely)
        return str(uuid.uuid4())


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

    def put(self, dynamo_item: CommandItem):
        '''
        Handles storing the given dynamo_item representing the audio command, as well as storing the anonymized version
        of the command.
        '''

        if (not self.enabled):
            return None

        detailed_item = dynamo_item.getDict()
        anonymous_item = dynamo_item.to_anonymous_command_item().getDict()

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
                key_value = {}
                key_value[self.primary_key] = key

                batch.delete_item(
                    Key = key_value
                )
