from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class StupidQuestionsConfig(BaseModel):
    """Validated subreddit polling settings for the StupidQuestions module."""

    model_config = ConfigDict(extra="forbid")

    subreddits: list[str] = Field(default_factory=lambda: ["NoStupidQuestions"])
    top_time: str = "month"
    submission_count: PositiveInt = 500
    refresh_time_seconds: PositiveInt = 21_600
