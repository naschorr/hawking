from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class FFmpegConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameters: str = "-ac 2 -guess_layout_max 0"
    post_parameters: str = "-loglevel 16"


class AudioPlayerConfig(BaseModel):
    """Validated settings for voice playback and inactivity handling."""

    model_config = ConfigDict(extra="forbid")

    channel_timeout_seconds: PositiveInt = 900
    skip_percentage: float = Field(default=0.5, ge=0.0, le=1.0)
    ffmpeg: FFmpegConfig = Field(default_factory=FFmpegConfig)
