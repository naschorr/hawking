from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hawking.core.services.configuration.validators import resolve_config_path, validate_directory_exists


class PhrasesConfig(BaseModel):
    """Validated phrase module settings."""

    model_config = ConfigDict(extra="forbid")

    directory_path: Path
    minimum_similarity: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity_algorithm: str = "difflib"

    @field_validator("directory_path", mode="before")
    @classmethod
    def validate_directory_path(cls, value: str | Path) -> Path:
        path = "code/addons/phrases/phrases" if value == "" else value
        return validate_directory_exists(resolve_config_path(path))
