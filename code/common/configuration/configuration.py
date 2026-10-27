import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from confiddle import (
    ConfigEnvironment,
    Confiddle,
    ConfiddleConfigModel,
    JsonProviderConfig,
    ProviderConfigModel,
)
from confiddle.utilities.dict_merger import DictMerger
from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.app_config import AppConfig
from common.audio_player_config import AudioPlayerConfig
from common.cogs.admin_cog_config import AdminCogConfig
from common.cogs.invite_cog_config import InviteCogConfig
from common.cogs.privacy_management_cog_config import PrivacyManagementCogConfig
from common.database.database_manager_config import DatabaseManagerConfig
from common.discord_config import DiscordConfig
from common.logging_config import LoggingConfig
from common.module.module_manager_config import ModuleManagerConfig
from core.cogs.speech_cog_config import SpeechConfig
from core.tts.tts_controller_config import TTSControllerConfig
from modules.phrases.phrases_config import PhrasesConfig
from modules.reddit.reddit_config import RedditConfig
from modules.stupid_questions.stupid_questions_config import StupidQuestionsConfig
from common import utilities


class HawkingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppConfig = Field(default_factory=AppConfig)
    discord: DiscordConfig
    audio: AudioPlayerConfig = Field(default_factory=AudioPlayerConfig)
    logging: LoggingConfig
    privacy: PrivacyManagementCogConfig
    database: DatabaseManagerConfig
    module_loader: ModuleManagerConfig = Field(default_factory=ModuleManagerConfig)
    invite: InviteCogConfig
    admin: AdminCogConfig = Field(default_factory=AdminCogConfig)


class HawkingModules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speech: SpeechConfig = Field(default_factory=SpeechConfig)
    tts: TTSControllerConfig
    phrases: PhrasesConfig
    reddit: RedditConfig
    stupid_questions: StupidQuestionsConfig = Field(default_factory=StupidQuestionsConfig)


class _HawkingConfigSources(BaseModel):
    """Unvalidated nested source data, merged by Confiddle before schema validation."""

    model_config = ConfigDict(extra="forbid")

    hawking: dict[str, Any] = Field(default_factory=dict)
    modules: dict[str, Any] = Field(default_factory=dict)


class HawkingConfig(BaseModel):
    """Typed root model for the complete Hawking configuration tree."""

    model_config = ConfigDict(extra="forbid")

    hawking: HawkingSettings
    modules: HawkingModules

    @model_validator(mode="before")
    @classmethod
    def populate_shared_app_fields(cls, value):
        if not isinstance(value, dict):
            return value

        hawking = value.get("hawking")
        modules = value.get("modules")
        if not isinstance(hawking, dict) or not isinstance(modules, dict):
            return value

        app = hawking.get("app", {})
        app = app if isinstance(app, dict) else {}
        app_name = app.get("name")
        app_version = app.get("version")

        logging_config = hawking.get("logging")
        if isinstance(logging_config, dict) and app_name:
            logging_config.setdefault("service_name", app_name)

        reddit_config = modules.get("reddit")
        if isinstance(reddit_config, dict) and app_version:
            reddit_config.setdefault("version", app_version)

        return value


@lru_cache(maxsize=4)
def load_hawking_config(config_directory: Path | None = None) -> HawkingConfig:
    """Load the root model using Confiddle's base and environment JSON providers."""

    config_path = config_directory or utilities.get_root_path()
    config_path = config_path.resolve()
    base_filename = config_path.name if config_path.is_file() else "config.json"
    root = config_path.parent if config_path.is_file() else config_path
    environment = ConfigEnvironment(os.getenv("HAWKING_ENV", "dev").lower())

    def load_provider(provider: JsonProviderConfig) -> dict[str, Any]:
        confiddle = Confiddle(ConfiddleConfigModel(
            bootstrap=ProviderConfigModel(),
            app=ProviderConfigModel(json_file_provider=[provider]),
            environment=environment,
        ))
        return confiddle.load_config(_HawkingConfigSources).model_dump()

    base_config = load_provider(JsonProviderConfig(
        directory_path=root,
        filename_template=base_filename,
    ))
    environment_config = load_provider(JsonProviderConfig(
        directory_path=root,
        filename_template="config.{environment}.json",
    ))
    merged_config = DictMerger.deep_merge(base_config, environment_config)
    return HawkingConfig.model_validate(merged_config)