from functools import lru_cache
from pathlib import Path
from typing import Any

from confiddle import (
    ConfigEnvironment,
    Confiddle,
    ConfiddleConfigModel,
    EnvVarProviderConfig,
    JsonProviderConfig,
    ProviderConfigModel,
)
from confiddle.utilities.dict_merger import DictMerger
from pydantic import BaseModel, ConfigDict, Field, model_validator

from hawking.core.services.configuration.app_config import AppConfig
from hawking.core.modules.audio_player.audio_player_cog_config import AudioPlayerConfig
from hawking.core.modules.admin.admin_cog_config import AdminCogConfig
from hawking.core.modules.invite.invite_cog_config import InviteCogConfig
from hawking.core.modules.privacy.privacy_cog_config import PrivacyManagementCogConfig
from hawking.core.services.database.database_manager_config import DatabaseManagerConfig
from hawking.core.services.configuration.aws_config import AwsConfig
from hawking.core.services.configuration.discord_config import DiscordConfig
from hawking.core.services.logging.logging_config import LoggingConfig
from hawking.core.services.module_manager.module_manager_config import ModuleManagerConfig
from hawking.core.services.string_similarity.string_similarity_config import StringSimilarityConfig
from hawking.modules.speech.speech_cog_config import SpeechConfig
from hawking.services.tts_manager.tts_controller_config import TTSControllerConfig
from hawking.core.utilities import utilities


class HawkingCoreSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppConfig = Field(default_factory=AppConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    aws: AwsConfig = Field(default_factory=AwsConfig)
    audio: AudioPlayerConfig = Field(default_factory=AudioPlayerConfig)
    logging: LoggingConfig
    privacy: PrivacyManagementCogConfig
    database: DatabaseManagerConfig
    module_loader: ModuleManagerConfig = Field(default_factory=ModuleManagerConfig)
    string_similarity: StringSimilarityConfig = Field(default_factory=StringSimilarityConfig)
    invite: InviteCogConfig
    admin: AdminCogConfig = Field(default_factory=AdminCogConfig)


class HawkingModules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speech: SpeechConfig = Field(default_factory=SpeechConfig)
    tts: TTSControllerConfig


class HawkingPackageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core: HawkingCoreSettings
    modules: HawkingModules


class _HawkingConfigSources(BaseModel):
    """Raw JSON data merged by Confiddle before full model validation."""

    model_config = ConfigDict(extra="forbid")

    hawking: dict[str, Any] = Field(default_factory=dict)
    addons: dict[str, Any] = Field(default_factory=dict)


class HawkingConfig(BaseModel):
    """Typed root model for the complete Hawking configuration tree."""

    model_config = ConfigDict(extra="forbid")

    hawking: HawkingPackageConfig
    addons: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def populate_shared_app_fields(self):
        app = self.hawking.core.app

        if "service_name" not in self.hawking.core.logging.model_fields_set and app.name:
            self.hawking.core.logging.service_name = app.name

        return self


def _detect_config_environment(config_directory: Path) -> ConfigEnvironment:
    """Infer the environment from the sole environment-specific config file."""

    environment_files = sorted(config_directory.glob("config.*.json"))
    if not environment_files:
        return ConfigEnvironment.DEV
    if len(environment_files) > 1:
        filenames = ", ".join(path.name for path in environment_files)
        raise ValueError(
            "Expected at most one environment-specific config file, "
            f"but found: {filenames}. Keep only the override for this deployment."
        )

    environment_name = environment_files[0].name.removeprefix("config.").removesuffix(".json")
    try:
        return ConfigEnvironment(environment_name)
    except ValueError as error:
        supported = ", ".join(environment.value for environment in ConfigEnvironment)
        raise ValueError(
            f"Unsupported config environment '{environment_name}'. Supported environments: {supported}."
        ) from error


@lru_cache(maxsize=4)
def load_hawking_config(config_directory: Path | None = None) -> HawkingConfig:
    """Load the root model using Confiddle's base and environment JSON providers."""

    if config_directory is None:
        root_path = utilities.get_root_path()
        config_path = root_path / "configuration"
        if not (config_path / "config.json").is_file():
            config_path = root_path
    else:
        config_path = config_directory
    config_path = config_path.resolve()
    base_filename = config_path.name if config_path.is_file() else "config.json"
    root = config_path.parent if config_path.is_file() else config_path
    environment = _detect_config_environment(root)

    def load_provider(
        provider: JsonProviderConfig,
    ) -> dict[str, Any]:
        confiddle = Confiddle(
            ConfiddleConfigModel(
                bootstrap=ProviderConfigModel(),
                app=ProviderConfigModel(json_file_provider=[provider]),
                environment=environment,
            )
        )
        return confiddle.load_config(_HawkingConfigSources).model_dump()

    base_config = load_provider(
        JsonProviderConfig(
            directory_path=root,
            filename_template=base_filename,
        )
    )
    environment_config = load_provider(
        JsonProviderConfig(
            directory_path=root,
            filename_template="config.{environment}.json",
        )
    )
    environment_confiddle = Confiddle(
        ConfiddleConfigModel(
            bootstrap=ProviderConfigModel(),
            app=ProviderConfigModel(
                env_var_provider=[EnvVarProviderConfig(delimiter="__")]
            ),
            environment=environment,
        )
    )
    environment_variables = environment_confiddle.load_config(
        _HawkingConfigSources
    ).model_dump(exclude_defaults=True)
    merged_config = DictMerger.deep_merge(
        DictMerger.deep_merge(base_config, environment_config), environment_variables
    )
    return HawkingConfig.model_validate(merged_config)
