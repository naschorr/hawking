import re
import emoji

import utilities

## Config
CONFIG_OPTIONS = utilities.load_config()


class MessageParser:
    ## Keys
    REPLACE_EMOJI_KEY = "replace_emoji"

    def __init__(self):
        self.replace_emoji = CONFIG_OPTIONS.get(self.REPLACE_EMOJI_KEY, True)

        ## Invert emoji.UNICODE_EMOJI's emoji dict
        self.emoji_map = {}
        for emoji_code, emoji_name in emoji.UNICODE_EMOJI.items():
            self.emoji_map[emoji_code.lower()] = self._strip_underscores(emoji_name[1:-1])

    ## Methods

    ## Parses a given message, replacing discord mentions with their proper names, and replacing emoji with their
    ## textual names.
    def parse_message(self, message, ctx):
        message = self._replace_mentions(message, ctx)

        if(self.replace_emoji):
            message = self._replace_emoji(message)
        else:
            message = self._strip_emoji(message)

        return message


    ## Removes all underscores from a string, and replaces them with spaces.
    def _strip_underscores(self, string):
        return re.sub(r"_", " ", string)


    ## Replaces emoji with their actual strings
    def _replace_emoji(self, message):
        char_array = list(message)

        for index, char in enumerate(char_array):
            char_lower = char.lower()

            if(char_lower in self.emoji_map):
                char_array[index] = self.emoji_map[char_lower]

        return ''.join(char_array)


    ## Removes all emoji from a given string
    def _strip_emoji(self, message):
        char_array = list(message)

        for index, char in enumerate(char_array):
            char_lower = char.lower()

            if(char_lower in self.emoji_map):
                del char_array[index]

        return ''.join(char_array)


    ## Replaces user.id mention strings with their actual names
    def _replace_mentions(self, message, ctx):
        ## In string, replace instances of discord_id with replacement
        def replace_id_with_string(string, discord_id, replacement):
            match = re.search("<@[!|&]?({})>".format(discord_id), string)
            if(match):
                start, end = match.span(0)
                string = string[:start] + replacement + string[end:]

            return string

        for user in ctx.mentions:
            message = replace_id_with_string(message, user.id, user.nick if user.nick else user.name)

        for channel in ctx.channel_mentions:
            message = replace_id_with_string(message, channel.id, channel.name)

        for role in ctx.role_mentions:
            message = replace_id_with_string(message, role.id, role.name)

        return message
