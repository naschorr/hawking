import os
import logging
import boto3
from pathlib import Path
from boto3.dynamodb.conditions import Key

from common.configuration import Configuration
from common.logging import Logging
from common.database.database_client import DatabaseClient
from common.database.factories.anonymous_item_factory import AnonymousItemFactory
from common.database.models.anonymous_item import AnonymousItem
from common.database.models.detailed_item import DetailedItem

## Config & logging
CONFIG_OPTIONS = Configuration.load_config(Path(__file__).parent)
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class DynamoDbClient(DatabaseClient):
    def __init__(self):
        name = CONFIG_OPTIONS.get("name", "bot").capitalize()
        self._detailed_table_name = CONFIG_OPTIONS.get("database_detailed_table_name", name)
        self._anonymous_table_name = CONFIG_OPTIONS.get("database_anonymous_table_name", f"{name}Detailed")
        self._detailed_table_ttl_seconds = CONFIG_OPTIONS.get("database_detailed_table_ttl_seconds", 31536000)   ## One year

        self.resource = CONFIG_OPTIONS.get('dynamo_db_resource', 'dynamodb')
        self.region_name = CONFIG_OPTIONS.get('dynamo_db_region_name', 'us-east-2')
        self.primary_key = CONFIG_OPTIONS.get('dynamo_db_primary_key', 'QueryId')

        if (credentials_path := CONFIG_OPTIONS.get('dynamo_db_credentials_file_path')):
            os.environ['AWS_SHARED_CREDENTIALS_FILE'] = credentials_path

        self.dynamo_db = boto3.resource(self.resource, region_name=self.region_name)
        self.detailed_table = self.dynamo_db.Table(self.detailed_table_name)
        self.anonymous_table = self.dynamo_db.Table(self.anonymous_table_name)

    ## Implemented Properties

    @property
    def detailed_table_name(self) -> str:
        return self._detailed_table_name


    @property
    def anonymous_table_name(self) -> str:
        return self._anonymous_table_name


    @property
    def detailed_table_ttl_seconds(self) -> int:
        return self._detailed_table_ttl_seconds

    ## Implemented Methods

    async def store(self, detailed_item: DetailedItem, anonymous_item: AnonymousItem):
        """
        Handles storing the given detailed item data into the Detailed table, as well as anonymizing the data and
        storing it in the Anonymous table.
        """

        ## TTL is DetailedItem only, so no need to worry about the AnonymousItem
        ttl_expiry_timestamp = int(detailed_item.created_at.timestamp() + self.detailed_table_ttl_seconds)

        detailed_item_json = detailed_item.to_json()
        detailed_item_json[self.primary_key] = detailed_item.build_primary_key()
        detailed_item_json["expires_on"] = ttl_expiry_timestamp
        try:
            LOGGER.debug(f"Storing detailed data in {self.detailed_table_name}, {detailed_item_json}")
            self.detailed_table.put_item(Item=detailed_item_json)
        except Exception as e:
            LOGGER.exception(f"Exception while storing anonymous data into {self.detailed_table_name}", exc_info=e)

        anonymous_item_json = anonymous_item.to_json()
        anonymous_item_json[self.primary_key] = anonymous_item.build_primary_key()
        try:
            LOGGER.debug(f"Storing anonymous data in {self.anonymous_table_name}, {anonymous_item_json}")
            self.anonymous_table.put_item(Item=anonymous_item_json)
        except Exception as e:
            LOGGER.exception(f"Exception while storing anonymous data into {self.anonymous_table_name}", exc_info=e)


    async def batch_delete_users(self, user_ids: list[str]):
        """
        Handles deleting all of the listed primary_keys from the supplied table in a batch operation. Note that this
        only works for tables that only use a primary partition key, if you've got additional keys then this will fail
        out.
        """

        if (not user_ids):
            LOGGER.warning("No user_ids provided, unable to batch delete users")
            return

        LOGGER.info(f"Starting to process {len(user_ids)} delete requests")
        primary_keys_to_delete = list(map(
            lambda item: item[self.primary_key],
            await self.get_keys_from_users(self.detailed_table, user_ids)
        ))

        LOGGER.info(f"Starting to batch delete {len(primary_keys_to_delete)} documents.")

        with self.detailed_table.batch_writer() as batch:
            for key in primary_keys_to_delete:
                key_value = {self.primary_key: key}

                batch.delete_item(
                    Key = key_value
                )

    ## Methods

    def build_multi_user_filter_expression(self, user_ids: list[str] = None):
        """
        Builds a multi user filter expression for querying the database. User ids are OR'd together, so that any
        document matching any part of the filter will be returned.
        """

        if (not user_ids):
            return None

        filter_expression = Key('user_id').eq(user_ids[0])
        for user_id in user_ids[1:]:
            filter_expression |= Key('user_id').eq(user_id)

        return filter_expression


    async def get_keys_from_users(self, table, user_ids: list[str] = None) -> list[str]:
        """Performs a lookup on the supplied table to determine what primary key each user_id corresponds to"""

        if (not user_ids):
            return

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
