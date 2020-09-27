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

    ## Defaults
    BOTO_ENABLE = CONFIG_OPTIONS.get(BOTO_ENABLE_KEY, False)
    BOTO_RESOURCE = CONFIG_OPTIONS.get(BOTO_RESOURCE_KEY, "dynamodb")
    BOTO_REGION_NAME = CONFIG_OPTIONS.get(BOTO_REGION_NAME_KEY, "us-east-2")
    BOTO_TABLE_NAME = CONFIG_OPTIONS.get(BOTO_TABLE_NAME_KEY, "Hawking")


    def __init__(self, **kwargs):
        self.enabled = kwargs.get(self.BOTO_ENABLE_KEY, self.BOTO_ENABLE)
        self.resource = kwargs.get(self.BOTO_RESOURCE_KEY, self.BOTO_RESOURCE)
        self.region_name = kwargs.get(self.BOTO_REGION_NAME_KEY, self.BOTO_REGION_NAME)
        self.table_name = kwargs.get(self.BOTO_TABLE_NAME_KEY, self.BOTO_TABLE_NAME)

        self.dynamo_db = boto3.resource(self.resource, region_name=self.region_name)
        self.table = self.dynamo_db.Table(self.table_name)

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
