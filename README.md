<p align="center"><img src="https://raw.githubusercontent.com/naschorr/hawking/master/resources/hawking-avatar.png" width="150"/></p>

# hawking
A retro text-to-speech bot for Discord, designed to work with all of the stuff you might've seen in Moonbase Alpha, using the existing commands.

Note that new Hawking activations are currently disabled. They'll be available again once I finish up the slash command upgrade (and potentially message content intent application).


## Join my Discord server!
Click [here](https://discord.gg/JJqx8C4) to join!
- Help me test unstable versions of Hawking and my other bots
- Let me know if something's broken
- Post suggestions for improving Hawking and my other bots
- Got a funny phrase you want added? Suggest it in there!

## Commands
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

## Hosting, Configuring, Commanding, and Extending Hawking (and more)!
- Take a look at the [Hawking installation guide](https://github.com/naschorr/hawking/blob/master/docs/installing_hawking.md)
- After you've got Hawking intalled, check out the [Hawking configuration guide](https://github.com/naschorr/hawking/blob/master/docs/configuring_hawking.md)
- Once Hawking has been configured, flex those admin muscles with the [admin command guide](https://github.com/naschorr/hawking/blob/master/docs/admin_commands.md) (_Hint:_ type in `\help admin`)
- Want to add features to your Hawking installation? Take a look at the [module building guide](https://github.com/naschorr/hawking/blob/master/docs/building_modules.md)!
- Check out the [privacy policy](https://github.com/naschorr/hawking/blob/master/docs/privacy_policy.md) too

## Lastly...
Also included are some built-in phrases from [this masterpiece](https://www.youtube.com/watch?v=1B488z1MmaA). Check out the `Phrases` section in the `\help` screen. You should also take a look at my dedicated [hawking-phrases repository](https://github.com/naschorr/hawking-phrases). It's got a bunch of phrase files that can easily be put into your phrases folder for even more customization.

Lastly, be sure to check out the [Moonbase Alpha](https://steamcommunity.com/sharedfiles/filedetails/?id=482628855) moon tunes guide on Steam, there's a bunch of great stuff in there!

Tested on Windows 10, and Ubuntu 16.04.
