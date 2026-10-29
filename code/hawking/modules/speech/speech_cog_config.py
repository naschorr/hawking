from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class SpeechConfig(BaseModel):
    """Validated settings for preparing text before it is sent to TTS."""

    model_config = ConfigDict(extra="forbid")

    prepend: str = "[:phoneme on]"
    append: str = ""
    character_limit: PositiveInt = 1250
    newline_replacement: str = "[_<250,10>]"
    replace_emoji: bool = True
    channel_timeout_phrases: list[str] = Field(default_factory=list)
