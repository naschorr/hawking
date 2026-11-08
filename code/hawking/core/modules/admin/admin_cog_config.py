from pydantic import BaseModel, ConfigDict, Field


class AdminCogConfig(BaseModel):
    """Validated settings for administrative commands."""

    model_config = ConfigDict(extra="forbid")

    admins: list[int] = Field(default_factory=list)
    announce_updates: bool = False
