from pydantic import BaseModel, ConfigDict, SecretStr, field_validator, model_validator


class AwsConfig(BaseModel):
    """Optional static AWS credentials loaded from the process environment."""

    model_config = ConfigDict(extra="forbid")

    access_key_id: SecretStr | None = None
    secret_access_key: SecretStr | None = None
    session_token: SecretStr | None = None

    @field_validator("access_key_id", "secret_access_key", "session_token", mode="before")
    @classmethod
    def normalize_empty_credentials(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_credential_pair(self):
        if bool(self.access_key_id) != bool(self.secret_access_key):
            raise ValueError("AWS access key ID and secret access key must be provided together.")
        if self.session_token and not self.access_key_id:
            raise ValueError("AWS session token requires access key ID and secret access key.")
        return self

    def to_boto3_kwargs(self) -> dict[str, str]:
        if not self.access_key_id or not self.secret_access_key:
            return {}

        credentials = {
            "aws_access_key_id": self.access_key_id.get_secret_value(),
            "aws_secret_access_key": self.secret_access_key.get_secret_value(),
        }
        if self.session_token:
            credentials["aws_session_token"] = self.session_token.get_secret_value()
        return credentials