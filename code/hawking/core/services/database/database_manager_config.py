from pydantic import ConfigDict

from hawking.core.services.database.clients.dynamo_db.dynamo_db_client_config import DynamoDbClientConfig


class DatabaseManagerConfig(DynamoDbClientConfig):
    """Database manager settings, including its configured storage backend."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
