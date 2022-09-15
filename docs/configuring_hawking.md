# Configuring Hawking
See `config.json` in the Hawking installation's root.

### Discord Configuration
- **name** - String - The bot's name.
- **version** - String - The bot's current semantic version.
- **admins** - Array - Array of Discord usernames who have access to `\admin` commands. Uses `Username#1234` format.
- **activation_str** - String - The string that'll activate the Discord bot from chat messages.
- **description** - Array - An array of strings making up the bot's description. Each element in the array goes on a new line in the help interface.
- **announce_updates** - Boolean - Choose whether or not the bot will announce status updates to the invoker's voice channel. Things like 'Loaded N phrases.' after invoking `\admin reload_phrases`.
- **delete_commands** - Boolean - Choose to delete the command that invoked the bot. This lets users operate the bot 'silently'. Requires that the bot role's `Manage Messages` permission is enabled, and that the bot can also 'Manage Messages' in the text chat channel.
- **channel_timeout** - Int - The time in seconds before the bot will leave its current voice channel due to inactivity.
- **channel_timeout_phrases** - Array - Array of strings that the bot can speak right before it leaves. One phrase is chosen randomly from the array.
- **skip_percentage** - Float - The minimum percentage of other users who need to request a skip before the currently playing audio will be skipped. Must be a floating point number between 0.0 and 1.0 inclusive.

### Bot Configuration
- **log_level** - String - The minimum error level to log. Potential values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`, in order of severity (ascending). For example, choosing the `WARNING` log level will log everything tagged as `WARNING`, `ERROR`, and `CRITICAL`.
- **log_path** - String - The path where logs should be stored. If left empty, it will default to a `logs` folder inside the Hawking root.
- **log_backup_count** - Int - The maximum number of logs to keep before deleting the oldest ones.
- **discord_token** - String - The token for the bot, used to authenticate with Discord.
- **delete_request_queue_file_path** - String - The path where the delete requests file should be stored. If left empty, it will default to a `privacy/delete_request.txt` file inside the Hawking root.
- **delete_request_meta_file_path** - String - The path where the delete requests metadata file should be stored. For example, this includes the time the delete request queue was last parsed. If left empty, it will default to a `privacy/metadata.json` file inside the Hawking root.
- **delete_request_weekday_to_process** - Integer - The integer corresponding to the day of the week to perform the delete request queue processing. 0 is Monday, 7 is Sunday, and so on.
- **delete_request_time_to_process** - String - The ISO8601 time string that specifies when the queue should be processed, when the provided day comes up each week. Make sure to use the format `THH:MM:SSZ`.
- **tts_executable** - String - The name of the text-to-speech executable.
- **\_tts_executable_path** - String - Force the bot to use a specific text-to-speech executable, rather than the normal `say.exe` file. Remove the leading underscore to activate it.
- **tts_output_dir** - String - The name of the file where the temporary speech files are stored.
- **\_tts_output_dir_path** - String - Force the bot to use a specific text-to-speech output folder, rather than the normal `temp/` folder. Remove the leading underscore to activate it.
- **audio_generate_timeout_seconds** - Int - Number of seconds to wait before timing out of the audio generation. Certain 'expanded' phrases can crash Hawking if too many are used at once (See: https://github.com/naschorr/hawking/issues/50)
- **ffmpeg_parameters** - String - Options to send to the FFmpeg executable before the `-i` flag. Used when building the audio player.
- **ffmpeg_post_parameters** - String - Options to send to the FFmpeg executable after the `-i` flag. Used when building the audio player.
- **output_extension** - String - The file extension of the text-to-speech engine's output.
- **wine** - String - The command to invoke Wine on your system. Linux only.
- **xvfb_prepend** - String - The string that'll select your `xvfb` display. Headless only.
- **headless** - Boolean - Indicate that the bot is running on a machine without a display. Uses `xvfb` to simulate a display required for the text-to-speech engine.
- **modules_dir** - String - The name of the directory, located in Hawking's root, which will contain the modules to dynamically load. See ModuleManager's discover() method for more info about how modules need to be formatted for loading.
- **\_modules_dir_path** - String - The path to the directory that contains the modules to be loaded for the bot. Remove the leading underscore to activate it.
- **string_similarity_algorithm** - String - The name of the algorithm to use when calculating how similar two given strings are. Currently only supports 'difflib'.
- **invalid_command_minimum_similarity** - Float - The minimum similarity an invalid command must have with an existing command before the existing command will be suggested as an alternative.
- **find_command_minimum_similarity** - Float - The minimum similarity the find command must have with an existing command, before the existing command will be suggested for use.
> *A quick note about minimum similarity*: If the value is set too low, then you can run into issues where seemingly irrelevant commands are suggested. Likewise, if the value is set too high, then commands might not ever be suggested to the user. For both of the minimum similarities, the value should be values between 0 and 1 (inclusive), and should rarely go below 0.4.

### Speech Configuration
- **prepend** - String - A string that'll always be prepended onto the text sent to the text-to-speech engine.
- **append** - String - A string that'll always be appended onto the text sent to the text-to-speech engine.
- **char_limit** - Int - A hard character limit for messages to be sent to the text-to-speech engine.
- **newline_replacement** - String - A string that'll replace all newline characters in the text sent to the text-to-speech engine.
- **replace_emoji** - Boolean - If `true`, indicates that the bot should convert emoji into their textual form (ex. :thinking: -> "thinking face"). This isn't a perfect conversion, as Discord encodes emoji into their unicode representation before the bot is able to parse it. If this is set to `false`, then the bot will just strip out emoji completely, as if they weren't there.

### Module Configuration
Modify the specified module's `config.json` file to update these properties.

#### Phrases Configuration
- **phrases_file_extension** - String - The file extension to look for when searching for phrase files. For example: `.json`.
- **phrases_folder** - String - The name of the folder that contains phrase files.
- **\_phrases_folder_path** - String - Force the bot to use a specific phrases folder, rather than the normal `phrases/` folder. Remove the leading underscore to activate it.

#### Reddit Configuration
You'll need to get access to the Reddit API via OAuth2, so follow the "First Steps" section of [this guide](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps) to get authenticated.

- **reddit_client_id** - String - This is the `client_id` provided to you by Reddit when you create the script.
- **reddit_secret** - String - This is the `secret` provided to you by Reddit when you create the script.
- **reddit_user_agent_platform** - String - The platform that your script will be running on. For example: `discord-bot-py`.
- **reddit_user_agent_app_id** - String - A unique identifier for the bot. For example: `hawking-tts`.
- **reddit_user_agent_contact_name** - String - The is the Reddit username that's associated with your script. For example, it should look something like `/u/this-is-my-username`.

All of the above `reddit*` properties are required to use the Reddit module, and thus any modules that depend on it (ex. the StupidQuestions module). Also, the user-agent that'll be sent to Reddit will be built from all of the user-agent properties above. For example, if you use the above examples, the the user-agent `discord-bot:hawking-tts:1.0.5 (by /u/this-is-my-username)` will be generated (assuming that you're running version 1.0.5 of Hawking). Lastly, please note that Reddit has some specific requirements about those user-agent components, so take a look at their [API guide](https://github.com/reddit-archive/reddit/wiki/API) for more details.

#### StupidQuestion Configuration
- **stupid_question_subreddits** - Array of Strings - An array of subreddit names to pull questions from, should be an array of length of at least one (and ideally that one is "NoStupidQuestions" or similar).
- **stupid_question_top_time** - String - Length of time to pull top posts from. Must be one of: `hour`, `day`, `week`, `month`, `year`, or `all`.
- **stupid_question_submission_count** - Int - The number of posts to retrieve when querying Reddit.
- **stupid_question_refresh_time_seconds** - Int - The number of seconds to wait before loading more questions.

### Analytics Configuration
- **database_enable** - Boolean - Indicate that you want the bot to upload analytics to an Amazon AWS resource.
- **database_credentials_file_path** - String - Path to your AWS credentials file, if it's not being picked up automatically. If empty, this will be ignored.
- **database_resource** - String - The AWS boto-friendly resource to upload to. (I've only tried DynamoDB, but I'm fairly sure AWS' other storage resources would work if you wanted to tweak the code).
- **database_region_name** - String - The AWS region of your chosen `database_resource`.
- **database_detailed_table_name** - String - The name of the table to insert detailed, temporary data into.
- **database_anonymous_table_name** - String - The name of the table to insert anonymized, long term data into.
- **database_primary_key** - String - The primary key of the above tables.
- **database_detailed_table_ttl_seconds** - Integer - The number of seconds before a record in the detailed table should be automatically removed via the DynamoDB TTL service.
