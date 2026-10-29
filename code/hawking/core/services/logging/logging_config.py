from pathlib import Path
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from hawking.core.services.configuration.validators import resolve_config_path, validate_directory_exists


class LoggingLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig(BaseModel):
    """Validated file logger settings."""

    model_config = ConfigDict(extra="forbid")

    level: LoggingLevel = LoggingLevel.DEBUG
    directory_path: Path = Field(default=Path("logs"), validate_default=True)
    backup_count: PositiveInt = 7
    service_name: str = Field(default="service", min_length=1)
    max_bytes: PositiveInt = 10_485_760

    @field_validator("directory_path", mode="before")
    @classmethod
    def resolve_directory(cls, value: str | Path) -> Path:
        return resolve_config_path(value)

    @field_validator("directory_path")
    @classmethod
    def validate_directory(cls, value: Path) -> Path:
        return validate_directory_exists(value)
