from pathlib import Path

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from hawking.core.services.configuration.validators import is_file_accessible, resolve_config_path


class DeleteRequestsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue_file_path: Path = Field(default=Path("privacy/delete_requests.txt"), validate_default=True)
    metadata_file_path: Path = Field(default=Path("privacy/meta.json"), validate_default=True)
    weekday_to_process: int = Field(default=0, ge=0, le=6)
    time_to_process: str = "T00:00:00Z"

    @field_validator("queue_file_path", "metadata_file_path", mode="before")
    @classmethod
    def _resolve_config_path(cls, value: Path | str) -> Path:
        return resolve_config_path(value)

    @field_validator("queue_file_path", "metadata_file_path")
    @classmethod
    def _validate_file_accessible(cls, value: Path) -> Path:
        if not is_file_accessible(value):
            raise ValueError(f"Configured file is not accessible: {value}")
        return value


class PrivacyManagementCogConfig(BaseModel):
    """Validated privacy settings consumed by PrivacyManagementCog."""

    model_config = ConfigDict(extra="forbid")

    policy_url: AnyHttpUrl
    delete_requests: DeleteRequestsConfig = Field(default_factory=DeleteRequestsConfig)
