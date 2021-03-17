<p align="center"><img src="https://raw.githubusercontent.com/naschorr/hawking/master/resources/hawking-avatar.png" width="150"/></p>

# hawking
A retro text-to-speech bot for Discord, designed to work with all of the stuff you might've seen in Moonbase Alpha, using the existing commands.

## Activate Hawking on your server!
- Go to [this page](https://discordapp.com/oauth2/authorize?client_id=334894709292007424&scope=bot&permissions=53803072) on Discord's site.
- Select the server that you want Hawking to be added to.
- Hit the "Authorize" button.
- Start speaking! (_Hint:_ join a voice channel and type in `\help`. You should check out the [**Commands**](https://github.com/naschorr/hawking#commands) section of this readme, too!)

## Join my Discord server!
Click [here](https://discord.gg/JJqx8C4) to join!
- Help me test unstable versions of Hawking and my other bots
- Let me know if something's broken
- Post suggestions for improving Hawking and my other bots
- Got a funny phrase you want added? Suggest it in there!

## Basic Commands
These commands allow for the basic operation of the bot, by anyone. Just type them into a public text channel while connected to a public voice channel. (Hawking can also read/join channels that you've given the permissions to)
- `\say [text]` - Tells the bot to speak [text] in the voice channel that you're currently in.
- `\skip` - Skip a phrase that you've requested, or start a vote to skip on someone else's phrase.
- `\find [text]` - The bot will search its preloaded phrases for the one whose contents most closely matches [text], and will display that command's name. Note: requires the Phrases module.
- `\random` - Plays a random phrase from the list of preloaded phrases. Note: requires the Phrases module.
- `\fortune` - Tells you your magic 8 ball fortune!
- `\stupidquestion` - Asks you a random, (potentially) stupid question from Reddit.
- `\invite` - Gets you an invite link for the bot, as well as gets you an invite link for my Discord server.
- `\delete_my_data` - Sets up a request to remove all of your stored user data (TTS data, User Id, Channel Id, and Server Id) from the Hawking database. Note that anonymized usage statistics are still kept, however. All requests are processed once a week, currently that happens every Monday at midnight. Furthermore, the previously mentioned identifying information will automatically be removed after a year.
- `\help` - Show the help screen.

## Hosting it yourself
- Make sure you've got [Python 3.6](https://www.python.org/downloads/) installed, and support for virtual environments (This assumes that you're on Python 3.6 with `venv` support, but Discord.py requires at least 3.5.3 currently)
- Double check that you're installing int a clean directory. If there's an old version of Hawking or an old venv then this likely won't work!
- `cd` into the directory that you'd like the project to go (If you're on Linux, I'd recommend '/usr/local/bin')
- `git clone https://github.com/naschorr/hawking`
- `python3.6 -m venv hawking/`
    + You may need to run: `apt install python3.6-venv` to enable virtual environments for Python 3.6 on Linux
- Activate your newly created venv
- `pip install -r requirements.txt`
    + If you run into issues during PyNaCl's installation, you may need to run: `apt install build-essential libffi-dev python3.6-dev` to install some supplemental features for the setup process.
- Make sure the [FFmpeg executable](https://www.ffmpeg.org/download.html) is in your system's `PATH` variable
- Create a [Discord app](https://discordapp.com/developers/applications/me), flag it as a bot, and put the bot token inside `config.json`, next to the `discord_token` key.
- Register the Bot with your server. Go to: `https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=53803072`, but make sure to replace CLIENT_ID with your bot's client id.
- Select your server, and hit "Authorize"
- Check out `config.json` for any configuration you might want to do. It's set up to work well out of the box, but you may want to add admins, change pathing, or modify the number of votes required for a skip.

#### Windows Installation
- Nothing else to do! Everything should work just fine.

#### Linux Installation
Running Hawking on Linux requires a bit more work. At a minimum you'll need some sort of way to get Windows applications running on Linux. However, if you plan to run Hawking in a server environment (and you probably do), you should also check out the [Server Installation](https://github.com/naschorr/hawking#server-installation) section below.

##### Basic Installation
- Install [Wine](https://www.winehq.org/) to get the text-to-speech executable working.
    + `dpkg --add-architecture i386`
    + `apt-get update`
    + `apt-get install wine`

##### Server Installation
- Get Hawking set up with Xvfb
    + Install Xvfb with with your preferred package manager (`apt install xvfb` on Ubuntu, for example)
    + Invoke Xvfb automatically on reboot with a cron job (`sudo crontab -e`), by adding `@reboot Xvfb :0 -screen 0 1024x768x16 &` to your list of jobs.
    + Set `headless` to be `true` in `config.json`
    + If you're using different virtual server or screen identifiers, then make sure they work with `xvfb_prepend` in `config.json`. Otherwise everything should work fine out of the box.

- Hawking as a Service (HaaS)
    > *Note:* This assumes that your system uses systemd. You can check that by running `pidof systemd && echo "systemd" || echo "other"` in the terminal. If your system is using sysvinit, then you can just as easily build a cron job to handle running `hawking.py` on reboot. Just make sure to use your virtual environment's Python executable, and not the system's one.

    - Assuming that your installation is in '/usr/local/bin/hawking', you'll want to move the `hawking.service` file into the systemd services folder with `mv hawking.service /etc/systemd/system/`
        + If your hawking installation is located elsewhere, just update the paths (`ExecStart` and `WorkingDirectory`) inside the `hawking.service` to point to your installation.
    - Get the service working with `sudo systemctl daemon-reload && systemctl enable hawking && systemctl start hawking --no-block`
    - Now you can control the Hawking service just like any other. For example, to restart: `sudo service hawking restart`

## Running your Hawking installation
- `cd` into the project's root
- Activate the venv (`source bin/activate` on Linux, `.\Scripts\activate` on Windows)
- `cd` into `hawking/code/` (Note, you need `hawking.py` to be in your current working directory, as there are some weird pathing issues with the required files for `say.exe`
- Run `python hawking.py` to start Hawking

## Admin Commands
Admin commands allow for some users to have a little more control over the bot. For these to work, the `admin` array in `config.json` needs to have the desired usernames added to it. Usernames should be in the `Username#1234` format that Discord uses.
- `\admin skip` - Skip whatever's being spoken at the moment, regardless of who requested it.
- `\admin reload_phrases` - Unloads, and then reloads the preset phrases (found in `phrases.json`). This is handy for quickly adding new presets on the fly.
- `\admin reload_cogs` - Unloads, and then reloads the cogs registered to the bot (see admin.py's register_module() method). Useful for debugging.
- `\admin disconnect` - Forces the bot to stop speaking, and disconnect from its current channel in the invoker's server.
- `\help admin` - Show the help screen for the admin commands.

## Configuration `config.json`

#### Discord Configuration
- **version** - String - The bot's current semantic version.
- **admins** - Array - Array of Discord usernames who have access to `\admin` commands. Uses `Username#1234` format.
- **activation_str** - String - The string that'll activate the Discord bot from chat messages.
- **description** - Array - An array of strings making up the bot's description. Each element in the array goes on a new line in the help interface.
- **announce_updates** - Boolean - Choose whether or not the bot will announce status updates to the invoker's voice channel. Things like 'Loaded N phrases.' after invoking `\admin reload_phrases`.
- **delete_commands** - Boolean - Choose to delete the command that invoked the bot. This lets users operate the bot 'silently'. Requires that the bot role's `Manage Messages` permission is enabled, and that the bot can also 'Manage Messages' in the text chat channel.
- **channel_timeout** - Int - The time in seconds before the bot will leave its current voice channel due to inactivity.
- **channel_timeout_phrases** - Array - Array of strings that the bot can speak right before it leaves. One phrase is chosen randomly from the array.
- **skip_percentage** - Float - The minimum percentage of other users who need to request a skip before the currently playing audio will be skipped. Must be a floating point number between 0.0 and 1.0 inclusive.

#### Bot Configuration
- **log_level** - String - The minimum error level to log. Potential values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`, in order of severity (ascending). For example, choosing the `WARNING` log level will log everything tagged as `WARNING`, `ERROR`, and `CRITICAL`.
- **log_path** - String - The path where logs should be stored. If left empty, it will default to a `logs` folder inside the Hawking root.
- **log_backup_count** - Int - The maximum number of logs to keep before deleting the oldest ones.
- **discord_token** - String - The token for the bot, used to authenticate with Discord.
- **delete_request_queue_file_path** - String - The path where the delete requests file should be stored. If left empty, it will default to a `privacy/delete_request.txt` file inside the Hawking root.
- **delete_request_meta_file_path** - String - The path where the delete requests metadata file should be stored. For example, this includes the time the delete request queue was last parsed. If left empty, it will default to a `privacy/metadata.json` file inside the Hawking root.
- **delete_request_weekday_to_process** - Integer - The integer corresponding to the day of the week to perform the delete request queue processing. 0 is Monday, 7 is Sunday, and so on.
- **delete_request_time_to_process** - String - The ISO8601 time string that specifies when the queue should be processed, when the provided day comes up each week. Make sure to use the format `THH:MM:SSZ`.
- **tts_file** - String - The name of the text-to-speech executable.
- **\_tts_file_path** - String - Force the bot to use a specific text-to-speech executable, rather than the normal `say.exe` file. Remove the leading underscore to activate it.
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

#### Speech Configuration
- **prepend** - String - A string that'll always be prepended onto the text sent to the text-to-speech engine.
- **append** - String - A string that'll always be appended onto the text sent to the text-to-speech engine.
- **char_limit** - Int - A hard character limit for messages to be sent to the text-to-speech engine.
- **newline_replacement** - String - A string that'll replace all newline characters in the text sent to the text-to-speech engine.
- **replace_emoji** - Boolean - If `true`, indicates that the bot should convert emoji into their textual form (ex. :thinking: -> "thinking face"). This isn't a perfect conversion, as Discord encodes emoji into their unicode representation before the bot is able to parse it. If this is set to `false`, then the bot will just strip out emoji completely, as if they weren't there.

#### Stupid Question Configuration
- **stupid_question_subreddits** - Array of Strings - An array of subreddit names to pull questions from, should be an array of length of at least one.

#### Analytics Configuration
- **database_enable** - Boolean - Indicate that you want the bot to upload analytics to an Amazon AWS resource.
- **database_credentials_file_path** - String - Path to your AWS credentials file, if it's not being picked up automatically. If empty, this will be ignored.
- **database_resource** - String - The AWS boto-friendly resource to upload to. (I've only tried DynamoDB, but I'm fairly sure AWS' other storage resources would work if you wanted to tweak the code).
- **database_region_name** - String - The AWS region of your chosen `database_resource`.
- **database_detailed_table_name** - String - The name of the table to insert detailed, temporary data into.
- **database_anonymous_table_name** - String - The name of the table to insert anonymized, long term data into.
- **database_primary_key** - String - The primary key of the above tables.
- **database_detailed_table_ttl_seconds** - Integer - The number of seconds before a record in the detailed table should be automatically removed via the DynamoDB TTL service.

#### Module Configuration
Modify the module's `config.json` file to update these properties.

##### Phrases Configuration
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

## Lastly...
Also included are some built-in phrases from [this masterpiece](https://www.youtube.com/watch?v=1B488z1MmaA). Check out the `Phrases` section in the `\help` screen. You should also take a look at my dedicated [hawking-phrases repository](https://github.com/naschorr/hawking-phrases). It's got a bunch of phrase files that can easily be put into your phrases folder for even more customization.

Lastly, be sure to check out the [Moonbase Alpha](https://steamcommunity.com/sharedfiles/filedetails/?id=482628855) moon tunes guide on Steam, there's a bunch of great stuff in there!

Tested on Windows 10, and Ubuntu 16.04.
