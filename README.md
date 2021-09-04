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
- `\speech_config` - Shows the help screen for configuring Hawking's speech.

## Admin Commands
Admin commands allow for some users to have a little more control over the bot. For these to work, the `admin` array in `config.json` needs to have the desired usernames added to it. Usernames should be in the `Username#1234` format that Discord uses.
- `\admin skip` - Skip whatever's being spoken at the moment, regardless of who requested it.
- `\admin reload_phrases` - Unloads, and then reloads the preset phrases (found in `phrases.json`). This is handy for quickly adding new presets on the fly.
- `\admin reload_cogs` - Unloads, and then reloads the cogs registered to the bot (see admin.py's register_module() method). Useful for debugging.
- `\admin disconnect` - Forces the bot to stop speaking, and disconnect from its current channel in the invoker's server.
- `\help admin` - Show the help screen for the admin commands.

## Hosting and Configuring Hawking
- Take a look at the [Hawking installation guide](https://github.com/naschorr/hawking/blob/master/docs/installing_hawking.md)
- After you've got Hawking intalled, check out the [Hawking configuration guide](https://github.com/naschorr/hawking/blob/master/docs/configuring_hawking.md)

## Lastly...
Also included are some built-in phrases from [this masterpiece](https://www.youtube.com/watch?v=1B488z1MmaA). Check out the `Phrases` section in the `\help` screen. You should also take a look at my dedicated [hawking-phrases repository](https://github.com/naschorr/hawking-phrases). It's got a bunch of phrase files that can easily be put into your phrases folder for even more customization.

Lastly, be sure to check out the [Moonbase Alpha](https://steamcommunity.com/sharedfiles/filedetails/?id=482628855) moon tunes guide on Steam, there's a bunch of great stuff in there!

Tested on Windows 10, and Ubuntu 16.04.
