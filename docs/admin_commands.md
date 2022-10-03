# Admin Commands
Admin commands allow for the bot owner to have convenient access to the bot from within Discord.

- `@Hawking admin sync_local` - Syncs the bot's slash commands to the user's current guild.
- `@Hawking admin sync_global` - Syncs the bot's slash commands to all guilds.
- `@Hawking admin clear_local` - Removes the bot's slash commands from the user'scurrent guild.
- `@Hawking admin skip` - Skip whatever's being spoken at the moment, regardless of who requested it.
- `@Hawking admin reload_phrases` - Unloads, and then reloads the preset phrases (found in the `phrases` module). This is handy for quickly adding new presets on the fly.
- `@Hawking admin reload_cogs` - Unloads, and then reloads the cogs registered to the bot (see admin.py's `register_module()` method). Useful for debugging.
- `@Hawking admin disconnect` - Forces the bot to stop speaking, and disconnect from its current channel in the invoker's server.
