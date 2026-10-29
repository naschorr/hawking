from pydantic import BaseModel, ConfigDict, Field


class DiscordConfig(BaseModel):
    """Validated Discord bot connection settings."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)
