import os
import boto3
import base64
import time
import logging

import utilities

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))

class DynamoItem:
    def __init__(self, discord_context, query, command, is_valid, error=None):
        author = discord_context.message.author
        channel = discord_context.message.channel
        guild = discord_context.message.guild

        self.user_id = int(author.id)
        self.user_name = "{}#{}".format(author.name, author.discriminator)
        self.timestamp = int(discord_context.message.created_at.timestamp() * 1000)
        self.channel_id = channel.id
        self.channel_name = channel.name
        self.server_id = guild.id
        self.server_name = guild.name

        self.query = query
        self.command = command
        self.is_valid = is_valid
        self.error = error

        self.primary_key_name = CONFIG_OPTIONS.get("boto_primary_key", "QueryId")
        self.primary_key = self.build_primary_key()

    ## Methods

    def getDict(self):
        output = {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "timestamp": self.timestamp,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "query": self.query,
            "command": self.command,
            "is_valid": self.is_valid
        }

        if(self.error != None):
            output["error"] = self.error

        output[self.primary_key_name] = self.primary_key

        return output


    def build_primary_key(self):
        concatenated = "{}{}".format(self.user_id, self.timestamp)

        return base64.b64encode(bytes(concatenated, "utf-8")).decode("utf-8")
    

class DynamoManager:
    ## Keys
    BOTO_ENABLE_KEY = "boto_enable"
    BOTO_RESOURCE_KEY = "boto_resource"
    BOTO_REGION_NAME_KEY = "boto_region_name"
    BOTO_TABLE_NAME_KEY = "boto_table_name"

    def __init__(self):
        self.enabled = CONFIG_OPTIONS.get('boto_enable', False)
        self.credentials_path = CONFIG_OPTIONS.get('boto_credentials_file_path')
        self.resource = CONFIG_OPTIONS.get('boto_resource', 'dynamodb')
        self.region_name = CONFIG_OPTIONS.get('boto_region_name', 'us-east-2')
        self.table_name = CONFIG_OPTIONS.get('boto_table_name', 'Hawking')

        self.dynamo_db = boto3.resource(self.resource, region_name=self.region_name)
        self.table = self.dynamo_db.Table(self.table_name)

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

    def put(self, dynamo_item):
        if(self.enabled):
            try:
                return self.table.put_item(Item=dynamo_item.getDict())
            except Exception as e:
                ## Don't let issues with dynamo tank the bot's functionality
                logger.exception("Exception while performing dynamo put")
                return None
        else:
            return None
