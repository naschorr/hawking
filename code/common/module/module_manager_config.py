from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.configuration.validators import resolve_config_path, validate_directory_exists as validate_directory_path


class ModuleManagerConfig(BaseModel):
    """Validated module discovery paths."""

    model_config = ConfigDict(extra="forbid")

    directory_path: Path = Field(default=Path("modules"), validate_default=True)

    @field_validator("directory_path", mode="before")
    @classmethod
    def resolve_directory_path(cls, value: str | Path) -> Path:
        return resolve_config_path(value)

    @field_validator("directory_path")
    @classmethod
    def validate_directory_exists(cls, value: Path) -> Path:
        return validate_directory_path(value)
