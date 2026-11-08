from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from hawking.core.services.configuration.validators import (
    resolve_config_path,
    validate_directory_path,
    validate_file_exists,
)


class TTSControllerConfig(BaseModel):
    """Validated settings owned by the TTS controller module."""

    model_config = ConfigDict(extra="forbid", validate_default=True)

    executable_path: Path
    output_directory_path: Path = Field(default=Path("temp"), validate_default=True)
    generate_timeout_seconds: PositiveInt = 3
    output_extension: str = "wav"
    args: dict[str, str] = Field(default_factory=dict)
    wine_command: str = "wine"
    xvfb_prepend: str = "DISPLAY=:0.0"
    headless: bool = False

    @field_validator("executable_path", mode="before")
    @classmethod
    def resolve_executable_path(cls, value: str | Path) -> Path:
        return resolve_config_path(Path(value).expanduser()).resolve()

    @field_validator("executable_path")
    @classmethod
    def validate_executable_path(cls, value: Path) -> Path:
        return validate_file_exists(value)

    @field_validator("output_directory_path", mode="before")
    @classmethod
    def resolve_output_directory_path(cls, value: str | Path) -> Path:
        return resolve_config_path(Path(value).expanduser()).resolve()

    @field_validator("output_directory_path")
    @classmethod
    def validate_output_directory_path(cls, value: Path) -> Path:
        return validate_directory_path(value)
