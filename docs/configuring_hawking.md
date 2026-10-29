# Configuring Hawking

Hawking reads configuration from `config.json` in the installation root. It then deep-merges the environment-specific `config.<environment>.json` file over it. The environment is selected with `HAWKING_ENV` and defaults to `dev`; for example, `HAWKING_ENV=production` loads `config.production.json`. Put shared, non-secret settings in `config.json` and environment-specific values or secrets in the matching override file. Do not commit credentials or bot tokens.

Settings are documented below by their exact dotted path in the JSON tree. Paths may be absolute or relative to the Hawking installation root unless noted otherwise.

The configuration mirrors the package layout: core settings are under `hawking.core`, built-in module settings are under `hawking.modules`, and optional addon settings are under `addons`.

## Core settings

### Application identity and UI (`hawking.core.app`)
- `hawking.core.app.name` - String - Bot name shared by the help and UI components.
- `hawking.core.app.version` - String - Hawking version. Also used in the Reddit user-agent string.
- `hawking.core.app.description` - Array of strings - Lines shown as the bot description in Discord.
- `hawking.core.app.repository_url` - Optional string - Repository link used by the help and UI components.
- `hawking.core.app.ui.accent_color_hex` - Hex string - Embed accent color parsed as a hexadecimal integer, normally without a leading `#`.

### Discord (`hawking.core.discord`)
- `hawking.core.discord.token` - Required non-empty string - Bot token used to authenticate with Discord.

### Voice playback (`hawking.core.audio`)
- `hawking.core.audio.channel_timeout_seconds` - Positive integer - Seconds of inactivity before Hawking leaves a voice channel.
- `hawking.core.audio.skip_percentage` - Number from `0.0` to `1.0` - Fraction of active non-bot listeners required to skip the current audio.
- `hawking.core.audio.ffmpeg.parameters` - String - FFmpeg arguments passed before the input-file argument.
- `hawking.core.audio.ffmpeg.post_parameters` - String - FFmpeg arguments passed after the input-file argument.

### Logging (`hawking.core.logging`)
- `hawking.core.logging.level` - `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` - Minimum level written to the log.
- `hawking.core.logging.directory_path` - Path - Log directory. It must already exist and be a directory.
- `hawking.core.logging.backup_count` - Positive integer - Number of rotated log files to retain.
- `hawking.core.logging.service_name` - Non-empty string - Log filename prefix. Defaults to `hawking.core.app.name` when omitted.
- `hawking.core.logging.max_bytes` - Positive integer - Present in the configuration schema, but currently unused; logging rotates on a time-based schedule.

### Privacy (`hawking.core.privacy`)
- `hawking.core.privacy.policy_url` - HTTP(S) URL - Link to the privacy policy.
- `hawking.core.privacy.delete_requests.queue_file_path` - Path - Delete-request queue file. Missing files and parent directories are created during validation.
- `hawking.core.privacy.delete_requests.metadata_file_path` - Path - Delete-request metadata file. Missing files and parent directories are created during validation.
- `hawking.core.privacy.delete_requests.weekday_to_process` - Integer from `0` to `6` - Day of the week to process the queue; `0` is Monday and `6` is Sunday.
- `hawking.core.privacy.delete_requests.time_to_process` - Time string - Scheduled processing time, formatted as `THH:MM:SSZ`.

### Analytics database (`hawking.core.database`)
- `hawking.core.database.enabled` - Boolean - Whether to record analytics.
- `hawking.core.database.detailed_table` - Non-empty string - DynamoDB table for detailed, temporary records.
- `hawking.core.database.anonymous_table` - Non-empty string - DynamoDB table for anonymized records.
- `hawking.core.database.detailed_table_ttl_seconds` - Positive integer - Record lifetime in the detailed table, in seconds.
- `hawking.core.database.dynamodb.credentials_file_path` - Path - Existing AWS credentials file. The current schema requires a file path; an empty value is not accepted. The path is relative to the Hawking root or absolute.
- `hawking.core.database.dynamodb.resource` - String - Boto3 resource name; normally `dynamodb`.
- `hawking.core.database.dynamodb.region_name` - String - AWS region containing the tables.
- `hawking.core.database.dynamodb.primary_key` - String - Partition-key attribute used by both tables.

### Module discovery (`hawking.core.module_loader`)
- `hawking.core.module_loader.directory_path` - Path - Existing directory containing dynamically loaded modules. Hawking does not create it.

### String similarity (`hawking.core.string_similarity`)
- `hawking.core.string_similarity.similarity_algorithm` - String - Selects the matching algorithm. `difflib` is implemented; `jaro-winkler` and `damerau-levenshtein` are accepted by the schema but are not implemented.

### Invite (`hawking.core.invite`)
- `hawking.core.invite.blurb` - Non-empty string - Text shown with the bot invite.
- `hawking.core.invite.invite_url` - HTTP(S) URL - Bot invite link.
- `hawking.core.invite.support_invite_url` - HTTP(S) URL - Support Discord invite link.

### Administration (`hawking.core.admin`)
- `hawking.core.admin.admins` - Array of integers - Discord user IDs allowed to use admin commands.

## Module settings

Built-in module settings mirror the `hawking/modules` package and are nested under `hawking.modules`.

### Speech (`hawking.modules.speech`)
- `hawking.modules.speech.prepend` - String - Text added before each message sent to the TTS engine.
- `hawking.modules.speech.append` - String - Text added after each message sent to the TTS engine.
- `hawking.modules.speech.character_limit` - Positive integer - Maximum input-message length accepted for speech generation.
- `hawking.modules.speech.newline_replacement` - String - Replacement text for newline characters before TTS.
- `hawking.modules.speech.replace_emoji` - Boolean - If true, convert emoji to text names; if false, strip them. Conversion depends on the emoji representation Discord provides.
- `hawking.modules.speech.channel_timeout_phrases` - Array of strings - Phrases from which one is selected when Hawking leaves a voice channel after inactivity.

### Text-to-speech engine (`hawking.modules.tts`)
- `hawking.modules.tts.executable_path` - Path - Required existing TTS executable, relative to the Hawking root or absolute.
- `hawking.modules.tts.output_directory_path` - Path - Directory for generated audio. It may be missing; Hawking creates it at startup. An existing non-directory path is rejected.
- `hawking.modules.tts.generate_timeout_seconds` - Positive integer - Maximum time allowed for generating an audio file. Excessive expanded phrases can cause generation to hang (see [issue 50](https://github.com/naschorr/hawking/issues/50)).
- `hawking.modules.tts.output_extension` - String - Extension used for generated audio files, normally `wav`.
- `hawking.modules.tts.wine_command` - String - Command used to invoke Wine on Linux.
- `hawking.modules.tts.xvfb_prepend` - String - Display environment prefix used for headless Linux operation.
- `hawking.modules.tts.headless` - Boolean - Whether to run the TTS engine through a virtual display.
- `hawking.modules.tts.args` - Object of string values - Accepted by the config model, but currently not used when constructing the TTS command.

### Phrases (`addons.phrases`)
- `addons.phrases.directory_path` - Required path or empty string - Existing phrase directory. An empty string selects the bundled phrase data directory under the installation root.
- `addons.phrases.minimum_similarity` - Number from `0.0` to `1.0` - Minimum match score for phrase lookup. Lower values can produce unrelated matches; higher values can prevent matches.

### Reddit (`addons.reddit`)

Create a Reddit script application and configure its OAuth2 details. See Reddit's [OAuth2 guide](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps) and [API guide](https://github.com/reddit-archive/reddit/wiki/API) for account and user-agent requirements.

- `addons.reddit.client_id` - Required non-empty string - Client ID provided by Reddit.
- `addons.reddit.client_secret` - Required non-empty string - Client secret provided by Reddit.
- `addons.reddit.user_agent.platform` - Non-empty string - Platform running the bot, for example `discord-bot-py`.
- `addons.reddit.user_agent.app_id` - Non-empty string - Identifier for the bot, for example `hawking-tts`.
- `addons.reddit.user_agent.contact_name` - Non-empty string - Contact name for the Reddit application, for example `/u/your-username`.
- `addons.reddit.version` - Non-empty string - Version component of the Reddit user-agent. Defaults to `hawking.app.version` when omitted.

The user-agent is assembled as `platform:app_id:version (by contact_name)`. Reddit settings are required by the Reddit module and by modules that depend on it, such as Stupid Questions.

### Stupid Questions (`addons.stupid_questions`)
- `addons.stupid_questions.subreddits` - Array of strings - Subreddits to query; configure at least one subreddit.
- `addons.stupid_questions.top_time` - String - Reddit listing period: `hour`, `day`, `week`, `month`, `year`, or `all`.
- `addons.stupid_questions.submission_count` - Positive integer - Maximum number of posts retrieved per query.
- `addons.stupid_questions.refresh_time_seconds` - Positive integer - Delay between question refreshes, in seconds.
