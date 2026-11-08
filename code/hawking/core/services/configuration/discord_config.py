from pydantic import BaseModel, ConfigDict, Field, SecretStr


class DiscordConfig(BaseModel):
    """Validated Discord bot connection settings."""

    model_config = ConfigDict(extra="forbid")

    token: SecretStr = Field(min_length=1)
