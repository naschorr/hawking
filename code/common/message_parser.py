from dataclasses import replace
import re
import emoji

from common import utilities
from common.configuration import Configuration
from common.module.module import Module

## Config
CONFIG_OPTIONS = Configuration.load_config()


class MessageParser(Module):
    ## Keys
    REPLACE_EMOJI_KEY = "replace_emoji"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.replace_emoji = CONFIG_OPTIONS.get(self.REPLACE_EMOJI_KEY, True)

        ## Invert emoji.UNICODE_EMOJI's emoji dict
        self.emoji_map = {}
        for emoji_code, emoji_name in emoji.UNICODE_EMOJI.items():
            self.emoji_map[emoji_code.lower()] = self._strip_underscores(emoji_name[1:-1])

    ## Methods

    ## Parses a given message, replacing discord mentions with their proper names, and replacing emoji with their
    ## textual names.
    def parse_message(self, message: str, interaction_data: dict):
        message = self.replace_mentions(message, interaction_data)

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


    def replace_mentions(
            self,
            message: str,
            interaction_data: dict,
            hide_mention_formatting = True,
            hide_meta_mentions = True,
            anonymize_mentions = False
    ):
        """Replaces raw mentions with their human readable version (ex: <@1234567890> -> name OR <@name>)"""

        ## In string, replace instances of discord_id with replacement
        def replace_id_with_string(string, discord_id, replacement):
            match = re.search(f"<[@|#][!|&]?({discord_id})>", string)
            if(match):
                if (hide_mention_formatting):
                    start, end = match.span(0)
                else:
                    start, end = match.span(1)

                string = string[:start] + replacement + string[end:]

            return string


        id_mapping = {}
        unique_mention_counter = 0

        ## Build the discord entity id to name mapping
        for user in interaction_data.get("resolved", {}).get("users", {}).values():
            id_mapping[user["id"]] = f"user{unique_mention_counter}" if anonymize_mentions else user["username"]

        for member in interaction_data.get("resolved", {}).get("members", {}).values():
            id_mapping[member["user"]["id"]] = f"member{unique_mention_counter}" if anonymize_mentions else member.get("nick") or member["user"]["username"]

        for channel in interaction_data.get("resolved", {}).get("channels", {}).values():
            id_mapping[channel["id"]] = f"channel{unique_mention_counter}" if anonymize_mentions else channel["name"]

        for role in interaction_data.get("resolved", {}).get("roles", {}).values():
            id_mapping[role["id"]] = f"role{unique_mention_counter}" if anonymize_mentions else role["name"]

        ## Perform the replacement!
        for discord_id, replacement in id_mapping.items():
            ## Replace any inline mentions (ex: <@1234567890>)
            message = replace_id_with_string(message, discord_id, replacement)

            ## Hide any option mentions (ex: 1234567890), as it's almost certainly a 'meta' command.
            ## Todo: improve this, it's kind of janky right now
            if (hide_meta_mentions):
                message = message.replace(discord_id, "")
            else:
                message = message.replace(discord_id, replacement)

        return message
