from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hawking.core.services.configuration.validators import resolve_config_path, validate_file_exists


class DynamoDbSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credentials_file_path: Path
    resource: str = "dynamodb"
    region_name: str = "us-east-2"
    primary_key: str = "QueryId"

    @field_validator("credentials_file_path")
    @classmethod
    def resolve_credentials_file_path(cls, value: Path) -> Path:
        return resolve_config_path(value.expanduser()).resolve()

    @field_validator("credentials_file_path")
    @classmethod
    def validate_credentials_file_path(cls, value: Path) -> Path:
        return validate_file_exists(value)



class DynamoDbClientConfig(BaseModel):
    """Validated table and connection settings for DynamoDB."""

    model_config = ConfigDict(extra="forbid")

    detailed_table: str = Field(min_length=1)
    anonymous_table: str = Field(min_length=1)
    detailed_table_ttl_seconds: int = Field(default=31_536_000, ge=1)
    dynamodb: DynamoDbSettings
