from pydantic import BaseModel, ConfigDict, Field


class RedditUserAgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1)
    app_id: str = Field(min_length=1)
    contact_name: str = Field(min_length=1)


class RedditConfig(BaseModel):
    """Validated Reddit API settings."""

    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    version: str = Field(default="1.0.0", min_length=1)
    user_agent: RedditUserAgentConfig
