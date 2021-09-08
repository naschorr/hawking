# Admin Commands
Admin commands allow for some users to have a little more control over the bot. For these to work, the `admin` array in `config.json` needs to have the desired usernames added to it. Usernames should be in the `Username#1234` format that Discord uses.

- `\admin skip` - Skip whatever's being spoken at the moment, regardless of who requested it.
- `\admin reload_phrases` - Unloads, and then reloads the preset phrases (found in `phrases.json`). This is handy for quickly adding new presets on the fly.
- `\admin reload_cogs` - Unloads, and then reloads the cogs registered to the bot (see admin.py's register_module() method). Useful for debugging.
- `\admin disconnect` - Forces the bot to stop speaking, and disconnect from its current channel in the invoker's server.
- `\help admin` - Show the help screen for the admin commands.