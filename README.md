# hawking
A retro text-to-speech interface bot for Discord, designed to work with all of the stuff you might've seen in Moonbase Alpha, using the existing commands.

## Activation
- Go to [this page](https://discordapp.com/oauth2/authorize?client_id=334894709292007424&scope=bot&permissions=0) on Discord's site.
- Select the server that you want Hawking to be added to.
- Hit the "Authorize" button.
- Start speaking! (you should check out the **Usage** and **Commands** sections of this readme, first)

## Installation
- Make sure you've got [Python 3.5](https://www.python.org/downloads/) or greater, and virtualenv installed (`pip install virtualenv`)
- `cd` into the directory that you'd like the project to go
- `git clone https://github.com/naschorr/hawking`
- `virtualenv hawking`
- Activate your newly created virtualenv
- `pip install -r requirements.txt`
- Make sure the [FFmpeg executable](https://www.ffmpeg.org/download.html) is in your system's `PATH` variable
- Create a [Discord app](https://discordapp.com/developers/applications/me), flag it as a bot, and put the bot token inside `hawking/token.json`
- Register the Bot with your server. Go to: `https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=0`, but make sure to replace CLIENT_ID with your bot's client id.
- Select your server, and hit "Authorize"
- Check out `config.json` for any configuration you might want to do. It's set up to work well out of the box, but you may want to add admins, change pathing, or modify the number of votes required for a skip.

#### Windows Installation
- Nothing else to do! Everything should work just fine.

#### Linux Installation
- Install [Wine](https://www.winehq.org/) to get the text-to-speech executable working.

#### Headless Installation
- Install Xvfb with with your preferred package manager (`apt install xvfb` on Ubuntu, for example)
- Invoke Xvfb automatically on reboot with a cron job (`sudo crontab -e`), by adding `@reboot Xvfb :0 -screen 0 1024x768x16 &` to your list of jobs.
- Set `headless` to be `true` in `config.json`
- If you're using different virtual server or screen identifiers, then make sure they work with `xvfb_prepend` in `config.json`. Otherwise everything should work fine out of the box.

## Usage
- `cd` into the project's root
- Activate the virtualenv
- `cd` into `hawking/code/` (Note, you need `hawking.py` to be in your current working directory, as theres some weird pathing issues with the required files for `say.exe`
- `python hawking.py`

## Commands
These commands allow for the basic operation of the bot, by anyone.
- `\say [text]` - Tells the bot to speak [text] in the voice channel that you're currently in.
- `\skip` - Skip a phrase that you've requested, or start a vote to skip on someone else's phrase.
- `\music [options] [notes]` - Sings the [notes] aloud. See music.py's music() command docstring for more info about music structure. Currently rewriting to be even more flexible.
- `\summon` - Summons the bot to join your voice channel.
- `\help` - Show the help screen.

## Admin Commands
Admin commands allow for some users to have a little more control over the bot. For these to work, the `admin` array in `config.json` needs to have the desired usernames added to it. Usernames should be in the `Username#1234` format that Discord uses.
- `\admin skip` - Skip whatever's being spoken at the moment, regardless of who requested it.
- `\admin reload_phrases` - Unloads, and then reloads the preset phrases (found in `phrases.json`). This is handy for quickly adding new presets on the fly.
- `\admin reload_cogs` - Unloads, and then reloads the cogs registered to the bot (see admin.py's register_module() method). Useful for debugging.
- `\help admin` - Show the help screen for the admin commands.


## Configuration `config.json`
- **admins** - Array - Array of Discord usernames who have access to `\admin` commands. Uses `Username#1234` format.
- **debug_level** - Int - The maximum threshold for printing debug statements to the terminal. Debug statements with a level of `0` are the most important, while staements with a level of `4` are the least important. See `debug_print()` in `utilities.py`.
- **announce_updates** - Boolean - Choose whether or not the bot will announce status updates to the invoker's voice channel. Things like 'Loaded N phrases.' after invoking `\admin reload_phrases`.
- **delete_commands** - Boolean - Choose to delete the command that invoked the bot. This lets users operate the bot 'silently'. Requires that the bot's `Manage Messages` permission is enabled.
- **wine** - String - The command to invoke Wine on your system. Linux only.
- **xvfb_prepend** - String - The string that'll select your `xvfb` display. Headless only.
- **headless** - Boolean - Indicate that the bot is running on a machine without a display. Uses `xvfb` to simulate a display required for the text-to-speech engine.

- **activation_str** - String - The string that'll activate the Discord bot from chat messages.
- **description** - String - The bot's description. This is seen in the help interface.
- **token_file** - String - The name of the file containing the bot's Discord token.
- **\_token_file_path** - String - Force the bot to use a specific token, rather than the normal `token.json` file. Remove the leading underscore to activate it.
- **phrases_file_extension** - String - The file extension to look for when searching for phrase files.
- **phrases_folder** - String - The name of the folder that contains phrase files.
- **\_phrases_folder_path** - String - Force the bot to use a specific phrases folder, rather than the normal `phrases/` folder. Remove the leading underscore to activate it.
- **tts_file** - String - The name of the text-to-speech executable.
- **\_tts_file_path** - String - Force the bot to use a specific text-to-speech executable, rather than the normal `say.exe` file. Remove the leading underscore to activate it.
- **tts_output_dir** - String - The name of the file where the temporary speech files are stored.
- **\_tts_output_dir_path** - String - Force the bot to use a specific text-to-speech output folder, rather than the normal `temp/` folder. Remove the leading underscore to activate it.

- **skip_votes** - Int - The minimum number of votes needed by a channel to skip the currently playing speech.
- **skip_percentage** - Int - The minimum percentage of other users who need to request a skip before the currently playing speech will be skipped.
- **ffmpeg_before_options** - String - Options to send to the FFmpeg executable before the `-i` flag.
- **ffmpeg_options** - String - Options to send to the FFmpeg executable after the `-i` flag.
- **channel_timeout** - Int - The time in seconds before the bot will leave its current voice channel due to inactivity.

- **prepend** - String - A string that'll always be prepended onto the text sent to the text-to-speech engine.
- **append** - String - A string that'll always be appended onto the text sent to the text-to-speech engine.
- **char_limit** - Int - A hard character limit for messages to be sent to the text-to-speech engine.
- **newline_replacement** - String - A string that'll replace all newline characters in the text sent to the text-to-speech engine.
- **output_extension** - String - The file extension of the text-to-speech engine's output.

- **bpm** - Int - The default bpm for `\music` commands.
- **octave** - Int - The default octave for `\music` commands.
- **tone** - Boolean - Choose to use pure tones for musical notes instead of a simulated voice singing the notes.
- **bad** - Boolean - Choose to make all `\music` commands comically worse. Think Cher's 'My Heart Will Go On' on the recorder.
- **bad_percent** - Int - The percentage that the `bad` command makes music worse by.

## Lastly...
Also included are some built-in phrases from [this masterpiece](https://www.youtube.com/watch?v=1B488z1MmaA). Check out the `Phrases` section in the `\help` screen. You should also take a look at my dedicated [hawking-phrases repository](https://github.com/naschorr/hawking-phrases). It's got a bunch of phrase files that can easily be put into your phrases folder for even more customization.

Lastly, be sure to check out the [Moonbase Alpha](https://steamcommunity.com/sharedfiles/filedetails/?id=482628855) moon tunes guide on Steam.

Tested on Windows 10, and Ubuntu 16.04.
