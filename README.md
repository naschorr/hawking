<p align="center"><img src="https://raw.githubusercontent.com/naschorr/hawking/master/resources/hawking-avatar.png" width="150"/></p>

# hawking
A retro text-to-speech bot for Discord, designed to work with all of the stuff you might've seen in Moonbase Alpha, using the existing commands.

Note that new Hawking activations are currently disabled. They'll be available again once I finish up the slash command upgrade (and potentially message content intent application).

## Activate Hawking on your server!
- Go to [this page](https://discordapp.com/oauth2/authorize?client_id=334894709292007424&scope=bot&permissions=53803072) on Discord's site.
- Select the server that you want Hawking to be added to.
- Hit the "Authorize" button.
- Start speaking! (_Hint:_ join a voice channel and type in `/help`. You should check out the [**Commands**](https://github.com/naschorr/hawking#commands) section of this readme, too!)

## Join my Discord server!
Click [here](https://discord.gg/JJqx8C4) to join!
- Help me test unstable versions of Hawking and my other bots
- Let me know if something's broken
- Post suggestions for improving Hawking and my other bots
- Got a funny phrase you want added? Suggest it in there!

## Commands
These commands allow for the basic operation of the bot, by anyone. Just type them into a public text channel while connected to a public voice channel! Note that Hawking now uses slash commands, so just typing the command into Discord won't work as expected. You must select the command, and it's extra options (if desired) individually.
- `/say <text>` - Tells the bot to speak [text] in the voice channel that you're currently in.
- `/skip` - Skip a phrase that you've requested, or start a vote to skip on someone else's phrase.
- `/phrase <name>` - Speaks the specific preset phrase. Note that the name will autocomplete, so phrases are easy to find.
- `/find <text>` - The bot will search its loaded phrases for the one whose contents most closely matches the provided text, and will play it.
- `/random` - Plays a random phrase from the list of preloaded phrases.
- `/fortune` - Tells you your magic 8 ball fortune!
- `/invite` - Gets you an invite link for the Hawking, as well as gets you an invite link for Hawking's Discord server.
- `/privacy_policy` - Gives you a link to Hawking's [privacy policy](https://github.com/naschorr/hawking/blob/master/docs/privacy_policy.md).
- `/speech_config` - Gives you a link to the [speech configuration documentation](https://github.com/naschorr/hawking/blob/master/docs/configuring_speech.md) for Hawking.
- `/stupid_question` - Asks you a random, (potentially) stupid question from Reddit.
- `/help` - Show the help screen.

## Hosting, Configuring, Commanding, and Extending Hawking (and more)!
- Take a look at the [Hawking installation guide](https://github.com/naschorr/hawking/blob/master/docs/installing_hawking.md)
- After you've got Hawking intalled, check out the [Hawking configuration guide](https://github.com/naschorr/hawking/blob/master/docs/configuring_hawking.md)
- Once Hawking has been configured, flex those admin muscles with the [admin command guide](https://github.com/naschorr/hawking/blob/master/docs/admin_commands.md) (_Hint:_ type in `\help admin`)
- Want to add features to your Hawking installation? Take a look at the [module building guide](https://github.com/naschorr/hawking/blob/master/docs/building_modules.md)!
- Check out the [privacy policy](https://github.com/naschorr/hawking/blob/master/docs/privacy_policy.md) too

## Lastly...
Also included are some built-in phrases from [this masterpiece](https://www.youtube.com/watch?v=1B488z1MmaA). Check out the `Phrases` section in the `/help` screen. You should also take a look at my dedicated [hawking-phrases repository](https://github.com/naschorr/hawking-phrases). It's got a bunch of phrase files that can easily be put into your phrases folder for even more customization.

Lastly, be sure to check out the [Moonbase Alpha](https://steamcommunity.com/sharedfiles/filedetails/?id=482628855) moon tunes guide on Steam, there's a bunch of great stuff in there!

Tested on Windows 10, and Ubuntu 16.04.
