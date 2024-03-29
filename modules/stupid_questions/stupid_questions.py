import logging
import random
import time
import asyncio
from pathlib import Path

from core.cogs.speech_cog import SpeechCog
from common.command_management.invoked_command import InvokedCommand
from common.command_management.invoked_command_handler import InvokedCommandHandler
from common.configuration import Configuration
from common.database.database_manager import DatabaseManager
from common.exceptions import ModuleLoadException
from common.logging import Logging
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_container import ModuleInitializationContainer
from common.ui.component_factory import ComponentFactory
from question import Question

import discord
from discord import app_commands, Interaction
from discord.ext.commands import Bot

## Config & logging
CONFIG_OPTIONS = Configuration.load_config(Path(__file__).parent)
LOGGER = Logging.initialize_logging(logging.getLogger(__name__))

class StupidQuestions(DiscoverableCog):
    THOUGHT_PROVOKING_STRINGS = [
        "🤔?",
        "have you ever pondered:",
        "what do you think about this:",
        "have you ever considered:",
        "do you ever wonder about this:",
        "have a nice long think about this one:",
        "what do you think scholars in a thousand years will think about this:",
        "do you ever wonder why we're here? No? Ok, well have a wonder about this:",
        "take a gander at this highly intelligent and deeply insightful question:",
        "it's now time for us to plant some daffodils of opinion on the roundabout of chat at the end of conversation street, and discuss:"
    ]

    def __init__(self, bot: Bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)

        self.bot = bot

        self.speech_cog: SpeechCog = kwargs.get('dependencies', {}).get('SpeechCog')
        assert (self.speech_cog is not None)
        self.invoked_command_handler: InvokedCommandHandler = kwargs.get('dependencies', {}).get('InvokedCommandHandler')
        assert(self.invoked_command_handler is not None)
        self.database_manager: DatabaseManager = kwargs.get('dependencies', {}).get('DatabaseManager')
        assert (self.database_manager is not None)
        self.component_factory: ComponentFactory = kwargs.get('dependencies', {}).get('ComponentFactory')
        assert(self.component_factory is not None)

        ## Handle Reddit dependency
        reddit_dependency = kwargs.get('dependencies', {}).get('Reddit')
        if (not reddit_dependency):
            LOGGER.info(f"No Reddit dependency provided, unable to load {self.__class__.__name__}.")
            self.successful = False
            return
        self.reddit = reddit_dependency.reddit
        if (not reddit_dependency.successful):
            self.successful = False
            return

        self.questions = []
        self.is_mid_question_refresh = False
        self.last_question_refresh_time = time.time()

        ## Load config data
        self.submission_top_time = CONFIG_OPTIONS.get("stupid_question_top_time", "month")
        self.submission_count = CONFIG_OPTIONS.get("stupid_question_submission_count", 500)
        self.refresh_time_seconds = CONFIG_OPTIONS.get("stupid_question_refresh_time_seconds", 21600)
        subreddits = CONFIG_OPTIONS.get("stupid_question_subreddits", ["NoStupidQuestions"])

        try:
            ## Use a multireddit to pull random post from any of the chosen subreddits
            self.subreddit = self.reddit.subreddit("+".join(subreddits))
        except Exception as e:
            raise ModuleLoadException("Unable to create reddit/subreddit instance", e)

        ## Load the questions for polling, async
        asyncio.create_task(self.load_questions())

        self.add_command(app_commands.Command(
            name="stupid_question",
            description=self.stupid_question_command.__doc__,
            callback=self.stupid_question_command
        ))


    async def load_questions(self) -> None:
        ## Don't try to pull more data from Reddit if it's already happening
        if (self.is_mid_question_refresh):
            LOGGER.debug("Skipping load_questions as they're already being refreshed.")
            return
        self.is_mid_question_refresh = True

        LOGGER.info(f"Loading questions from reddit: top({self.submission_top_time}), {self.submission_count} submissions")
        questions = []
        try:
            submission_generator = self.subreddit.top(self.submission_top_time, limit=self.submission_count)
        except Exception as e:
            LOGGER.exception("Unable to load submission from Reddit.", e)
            return

        for submission in submission_generator:
            questions.append(Question(submission.title, submission.subreddit.display_name, submission.shortlink))

        self.last_question_refresh_time = time.time()
        self.questions = questions
        self.is_mid_question_refresh = False

        LOGGER.info("{} questions loaded at {}".format(len(self.questions), time.asctime()))

    ## Commands

    async def stupid_question_command(self, interaction: Interaction):
        """Ask a stupid question, via Reddit."""

        if (len(self.questions) > 0):
            question = random.choice(self.questions)
        else:
            await self.database_manager.store(interaction, valid=False)
            if (self.is_mid_question_refresh):
                await interaction.response.send_message(f"Sorry <@{interaction.user.id}>, but I'm currently loading new questions from Reddit. Try again later.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Sorry <@{interaction.user.id}>, but I'm having trouble loading questions from Reddit. Try again in a bit.", ephemeral=True)
            return


        async def callback(invoked_command: InvokedCommand):
            if (invoked_command.successful):
                thought_provoking_string = random.choice(self.THOUGHT_PROVOKING_STRINGS)
                embed = self.component_factory.create_basic_embed(
                    description=f"{question.text}\n\nvia [/r/{question.subreddit}]({question.url})",
                    url=question.url
                )

                await self.database_manager.store(interaction)
                await interaction.response.send_message(
                    f"Hey <@{interaction.user.id}>, {thought_provoking_string}",
                    embed=embed
                )
            else:
                await self.database_manager.store(interaction, valid=False)
                await interaction.response.send_message(invoked_command.human_readable_error_message, ephemeral=True)

            now = time.time()
            question_refresh_time = 0#self.last_question_refresh_time + self.refresh_time_seconds
            if (now > question_refresh_time):
                LOGGER.debug(f"Question refresh task due, {now} > {question_refresh_time}")
                ## Note that fetching questions before the interaction has been responded to will cause the interaction
                ## to fail. This might be avoidable by using deferred responses, however that then locks you in to
                ## either an ephemeral response (or not), which can be frustrating if an error happens and you've locked
                ## in a non-ephemeral response.
                ##
                ## A workaround could be to leverage asyncpraw and do everything async, but getting the initial question
                ## loading logic to play nice is difficult. `asyncio.create_task` will always cancel out before the
                ## `async submission for subreddit(...):` will actually yield anything
                self.bot.loop.create_task(self.load_questions())


        action = lambda: self.speech_cog.say(question.text, author=interaction.user, ignore_char_limit=True, interaction=interaction)
        await self.invoked_command_handler.invoke_command(interaction, action, ephemeral=False, callback=callback)


def main() -> ModuleInitializationContainer:
    return ModuleInitializationContainer(StupidQuestions, dependencies=["Reddit", "SpeechCog", "InvokedCommandHandler", "DatabaseManager", "ComponentFactory"])
