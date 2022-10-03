from dis import disco
import json
import os
import re
import logging
import asyncio
import random
from pathlib import Path
from typing import Literal, Union

from common.command_management.invoked_command import InvokedCommand
from common.command_management.invoked_command_handler import InvokedCommandHandler
from common.configuration import Configuration
from common.database import dynamo_manager
from common.logging import Logging
from common.string_similarity import StringSimilarity
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_container import ModuleInitializationContainer
from modules.phrases.phrase_file_manager import PhraseFileManager
from modules.phrases.models.phrase_group import PhraseGroup
from modules.phrases.models.phrase import Phrase

import discord
from discord import Interaction
from discord.app_commands import autocomplete, Choice, describe

## Config & logging
CONFIG_OPTIONS = Configuration.load_config(Path(__file__).parent)
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))


class Phrases(DiscoverableCog):
    PHRASES_NAME = "phrases"
    PHRASE_COMMAND_NAME = "phrase"
    RANDOM_COMMAND_NAME = "random"
    FIND_COMMAND_NAME = "find"

    def __init__(self, hawking, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

        self.speech_cog = kwargs.get('dependencies', {}).get('Speech')
        assert (self.speech_cog is not None)
        self.admin_cog = kwargs.get('dependencies', {}).get('Admin')
        assert (self.admin_cog is not None)
        self.invoked_command_handler: InvokedCommandHandler = kwargs.get('dependencies', {}).get('InvokedCommandHandler')
        assert(self.invoked_command_handler is not None)

        self.phrase_file_manager = PhraseFileManager()
        self.dynamo_db = dynamo_manager.DynamoManager()

        self.phrases: dict[str, Phrase] = {}
        self.phrase_groups: dict[str, PhraseGroup] = {}
        self.find_command_minimum_similarity = float(CONFIG_OPTIONS.get('find_command_minimum_similarity', 0.5))
        self.phrases_folder_path = self.phrase_file_manager.phrases_folder_path

        ## Load and add the phrases
        self.init_phrases()
        self.add_phrase_commands()

        self.successful = True

        ## This decorator needs to reference the injected dependency, thus we're declaring the command here.
        @self.admin_cog.admin.command(no_pm=True)
        async def reload_phrases(ctx):
            """Reloads the bot's list of phrases"""

            count = self.reload_phrases()

            loaded_clips_string = "Loaded {} phrase{}.".format(count, "s" if count != 1 else "")
            await ctx.send(loaded_clips_string)
            self.dynamo_db.put_message_context(ctx)

            return (count >= 0)

    ## Methods

    def cog_unload(self):
        """Removes all existing phrases when the cog is unloaded"""

        self.remove_phrases()
        self.remove_phrase_commands()


    def reload_phrases(self):
        """Unloads all phrase commands from the bot, then reloads all of the phrases, and reapplies them to the bot"""

        self.remove_phrases()
        self.remove_phrase_commands()

        self.init_phrases()
        self.add_phrase_commands()


    def remove_phrases(self):
        """Unloads the preset phrases from the bot's command list."""

        self.phrases = {}
        self.phrase_groups = {}


    def add_phrase_commands(self):
        """Adds the phrase commands to the bot"""

        ## Don't register phrase commands if no phrases have been loaded!
        if (self.phrases):
            ## Add the random command
            self.bot.tree.add_command(discord.app_commands.Command(
                name=Phrases.RANDOM_COMMAND_NAME,
                description=self.random_command.__doc__,
                callback=self.random_command
            ))

            # Add the find command
            self.bot.tree.add_command(discord.app_commands.Command(
                name=Phrases.FIND_COMMAND_NAME,
                description=self.find_command.__doc__,
                callback=self.find_command
            ))

            ## Add the phrase command
            ## Wrap the phrase command to have access to self in the autocomplete decorator. Unfortunately the parameter
            ## description decorators must also be moved up here.
            ## todo: Investigate a workaround that's less ugly?
            @autocomplete(name=self._phrase_name_command_autocomplete)
            @describe(name="The name of the phrase to speak")
            @describe(user="The user to speak the phrase to")
            async def phrase_command_wrapper(interaction: Interaction, name: str, user: discord.Member = None):
                await self.phrase_command(interaction, name, user)

            self.bot.tree.add_command(discord.app_commands.Command(
                name=Phrases.PHRASE_COMMAND_NAME,
                description=self.phrase_command.__doc__,
                callback=phrase_command_wrapper,
                extras={"cog": self}
            ))


    def remove_phrase_commands(self):
        self.bot.tree.remove_command("random")
        self.bot.tree.remove_command(Phrases.PHRASE_COMMAND_NAME)
        self.bot.tree.remove_command("find")


    def init_phrases(self):
        """Initialize the phrases available to the bot"""

        phrase_group_file_paths = self.phrase_file_manager.discover_phrase_groups(self.phrases_folder_path)
        counter = 0
        for phrase_file_path in phrase_group_file_paths:
            starting_count = counter
            phrase_group = self.phrase_file_manager.load_phrase_group(phrase_file_path)

            phrase: Phrase
            for phrase in phrase_group.phrases.values():
                try:
                    self.phrases[phrase.name] = phrase
                except Exception as e:
                    LOGGER.warning("Skipping...", e)
                else:
                    counter += 1

            ## Ensure we don't add in empty phrase files into the groupings
            ## todo: this isn't necessary any more, is it?
            if(counter > starting_count):
                self.phrase_groups[phrase_group.key] = phrase_group

        LOGGER.info(f'Loaded {counter} phrase{"s" if counter != 1 else ""}.')
        return counter


    def build_phrase_command_string(self, phrase: Phrase, activation_str: str = None) -> str:
        return f"{activation_str or '/'}{Phrases.PHRASE_COMMAND_NAME} {phrase.name}"

    ## Commands

    @describe(user="The user to speak the phrase to")
    async def random_command(self, interaction: Interaction, user: discord.Member = None):
        """Speaks a random phrase"""

        # self.dynamo_db.put_message_context(ctx, False)
        phrase: Phrase = random.choice(list(self.phrases.values()))


        async def callback(invoked_command: InvokedCommand):
            if (invoked_command.successful):
                await interaction.followup.send(f"<@{interaction.user.id}> randomly chose **/{self.build_phrase_command_string(phrase)}**")
            else:
                await interaction.followup.send(invoked_command.human_readable_error_message)


        action = lambda: self.speech_cog.say(
            phrase.message,
            author=interaction.user,
            target_member=user,
            ignore_char_limit=True,
            interaction=interaction
        )
        await self.invoked_command_handler.handle_deferred_command(interaction, action, ephemeral=False, callback=callback)


    async def _phrase_name_command_autocomplete(self, interaction: Interaction, current: str) -> list[Choice]:
        def generate_choice(phrase: Phrase) -> Choice:
            return Choice(name=f"{phrase.name} - {phrase.help or phrase.brief}", value=phrase.name)


        if (current.strip() == ""):
            phrases = random.choices(list(self.phrases.values()), k=5)
            return [generate_choice(phrase) for phrase in phrases]
        else:
            return [generate_choice(phrase) for phrase in self.phrases.values() if phrase.name.startswith(current)]


    async def phrase_command(self, interaction: Interaction, name: str, user: discord.Member = None):
        """Speaks the specific phrase"""

        # self.dynamo_db.put_message_context(ctx, False)

        ## Get the actual phrase from the phrase name provided by autocomplete
        phrase: Phrase = self.phrases.get(name)
        command_string = self.build_phrase_command_string(phrase) if phrase else name

        if (phrase is None):
            await interaction.response.send_message(
                f"Sorry <@{interaction.user.id}>, **{command_string}** isn't a valid phrase.",
                ephemeral=True
            )


        async def callback(invoked_command: InvokedCommand):
            if (invoked_command.successful):
                await interaction.followup.send(f"<@{interaction.user.id}> used **{command_string}**")
            else:
                await interaction.followup.send(invoked_command.human_readable_error_message)


        action = lambda: self.speech_cog.say(
            phrase.message,
            author=interaction.user,
            target_member=user,
            ignore_char_limit=True,
            interaction=interaction
        )
        await self.invoked_command_handler.handle_deferred_command(interaction, action, ephemeral=False, callback=callback)


    @describe(search="The text to search the phrases for")
    @describe(user="The user to speak the phrase to, if a match is found")
    async def find_command(self, interaction: Interaction, search: str, user: discord.Member = None):
        """Speaks the most similar phrase"""

        def calc_substring_score(message: str, description: str) -> float:
            """Scores a given string (message) based on how many of it's words exist in another string (description)"""

            ## Todo: shrink instances of repeated letters down to a single letter in both message and description
            ##       (ex. yeeeee => ye or reeeeeboot => rebot)

            message_split = message.split(' ')
            word_frequency = sum(word in description.split(' ') for word in message_split)

            return word_frequency / len(message_split)


        # self.dynamo_db.put_message_context(ctx, False)

        raw_search = search
        ## Strip all non alphanumeric and non whitespace characters out of the message
        search = "".join(char for char in search.lower() if (char.isalnum() or char.isspace()))

        most_similar_phrase = (None, 0)
        phrase: Phrase
        for phrase in self.phrases.values():
            scores = []

            ## Score the phrase
            scores.append(
                calc_substring_score(search, phrase.name) + \
                StringSimilarity.similarity(search, phrase.name) / 2
            )
            if (phrase.description is not None):
                scores.append(
                    calc_substring_score(search, phrase.description) + \
                    StringSimilarity.similarity(search, phrase.description) / 2
                )

            distance = sum(scores) / len(scores)
            if (distance > most_similar_phrase[1]):
                most_similar_phrase = (phrase, distance)

        if (most_similar_phrase[1] < self.find_command_minimum_similarity):
            await interaction.response.send_message(f"Sorry <@{interaction.user.id}>, I couldn't find anything close to that.", ephemeral=True)
            return

        ## With the phrase found, prepare to speak it!

        async def callback(invoked_command: InvokedCommand):
            if (invoked_command.successful):
                await interaction.followup.send(
                    ## todo: this is really lazy
                    f"<@{interaction.user.id}> searched with **/find {raw_search}**, and found **{self.build_phrase_command_string(phrase)}**"),
            else:
                await interaction.followup.send(invoked_command.human_readable_error_message)


        action = lambda: self.speech_cog.say(
            phrase.message,
            author=interaction.user,
            target_member=user,
            ignore_char_limit=True,
            interaction=interaction
        )
        await self.invoked_command_handler.handle_deferred_command(interaction, action, ephemeral=False, callback=callback)


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(Phrases, dependencies=["Admin", "Speech", "InvokedCommandHandler"])
