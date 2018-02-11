import boto3
import base64
import time

import utilities

## Config
CONFIG_OPTIONS = utilities.load_config()

class DynamoItem:
    def __init__(self, discord_context, query, command, is_valid):
        author = discord_context.message.author
        channel = discord_context.message.channel
        server = discord_context.message.server

        self.user_id = int(author.id)
        self.user_name = "{}#{}".format(author.name, author.discriminator)
        self.timestamp = int(discord_context.message.timestamp.timestamp() * 1000)
        self.channel_id = channel.id
        self.channel_name = channel.name
        self.server_id = server.id
        self.server_name = server.name

        self.query = query
        self.command = command
        self.is_valid = is_valid

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
        output[self.primary_key_name] = self.primary_key

        return output


    def build_primary_key(self):
        concatenated = "{}{}".format(self.user, self.timestamp)

        return base64.b64encode(bytes(concatenated, "utf-8")).decode("utf-8")
    

class DynamoHelper:
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
                utilities.debug_print("Exception while performing dynamo put", e, debug_level=1)
                return None
        else:
            return None
