from pydantic import BaseModel, ConfigDict, Field


class ComponentUiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accent_color_hex: str = "000000"


class AppConfig(BaseModel):
    """Shared application identity and presentation settings."""

    model_config = ConfigDict(extra="forbid")

    name: str = "the bot"
    version: str = "1.0.0"
    description: list[str] = Field(default_factory=lambda: ["The retro TTS bot for Discord"])
    repository_url: str | None = None
    ui: ComponentUiConfig = Field(default_factory=ComponentUiConfig)