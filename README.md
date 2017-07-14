# hawking
A DECTalk interface bot for Discord, designed to do all of the text-to-speech stuff you might've seen in Moonbase Alpha, using existing commands.

## Installation
- Make sure you've got Python 3.5 or greater installed
- `git clone https://github.com/naschorr/hawking`
- `virtualenv hawking`
- Activate your newly created virtualenv
- `pip install requirements.txt`
- Make sure the [FFmpeg executable](https://www.ffmpeg.org/download.html) is in your PATH variable
- Create a Discord app, flag it as a bot, and put the bot token inside `hawking/token.json`
- Register the Bot with your server. Go to: `https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=0`, but make sure to replace CLIENT_ID with your bot's client id.
- Select your server, and enjoy.

## Usage
- Activate the virtualenv
- `cd` into `hawking/code/` (Note, you need `hawking.py` to be in your current working directory, as theres some weird pathing issues with the required files for `say.exe`
- `python hawking.py`

## Commands
- `\say [text]` - Tells the bot to speak [text] in the voice channel that you're currently in.
- `\summon` - Summons the bot to join your voice channel.
- `\help` - Show the help screen.

Also included are some built-in phrases from [this masterpiece](https://www.youtube.com/watch?v=1B488z1MmaA). Check out the `SpeechPreset` section in the `\help` screen.

Lastly, be sure to check out the [Moonbase Alpa](https://steamcommunity.com/sharedfiles/filedetails/?id=482628855) moon tunes guide on Steam.
