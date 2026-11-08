from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class RedditUserAgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1)
    app_id: str = Field(min_length=1)
    contact_name: str = Field(min_length=1)


class RedditConfig(BaseModel):
    """Validated Reddit API settings."""

    model_config = ConfigDict(extra="forbid")

    client_id: SecretStr = Field(min_length=1)
    client_secret: SecretStr = Field(min_length=1)
    version: str = Field(default="1.0.0", min_length=1)
    user_agent: RedditUserAgentConfig

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() == "replace-with-your-reddit-client-id":
            raise ValueError("Set ADDONS__REDDIT__CLIENT_ID in configuration/.env.")
        return value

    @field_validator("client_secret")
    @classmethod
    def validate_client_secret(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() == "replace-with-your-reddit-client-secret":
            raise ValueError("Set ADDONS__REDDIT__CLIENT_SECRET in configuration/.env.")
        return value
