from pydantic import BaseModel, ConfigDict, Field


class DynamoDbSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource: str = "dynamodb"
    region_name: str = "us-east-2"
    primary_key: str = "QueryId"


class DynamoDbClientConfig(BaseModel):
    """Validated table and connection settings for DynamoDB."""

    model_config = ConfigDict(extra="forbid")

    detailed_table: str = Field(min_length=1)
    anonymous_table: str = Field(min_length=1)
    detailed_table_ttl_seconds: int = Field(default=31_536_000, ge=1)
    dynamodb: DynamoDbSettings
