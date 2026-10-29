from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class InviteCogConfig(BaseModel):
    """Validated invite details used by InviteCog."""

    model_config = ConfigDict(extra="forbid")

    blurb: str = Field(min_length=1)
    invite_url: AnyHttpUrl
    support_invite_url: AnyHttpUrl
