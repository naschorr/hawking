import os
import logging
import random
import time

import utilities

import discord
from discord.ext import commands
from praw import Reddit

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class StupidQuestions(commands.Cog):
    REDDIT_USER_AGENT = "discord:hawking:{} (by /u/hawking-py)".format(CONFIG_OPTIONS.get("version", "0.0.1"))
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

    def __init__(self, hawking, bot, *args, **kwargs):
        self.hawking = hawking
        self.bot = bot 

        self.questions = []
        self.is_mid_question_refresh = False
        self.last_question_refresh_time = time.time()

        ## Load config data
        self.submission_top_time = CONFIG_OPTIONS.get("stupid_question_top_time", "month")
        self.submission_count = CONFIG_OPTIONS.get("stupid_question_submission_count", 500)
        self.refresh_time_seconds = CONFIG_OPTIONS.get("stupid_question_refresh_time_seconds", 21600)
        ## Load module specific configs from 'stupid_questions.json' located in modules folder
        modules_folder_name = CONFIG_OPTIONS.get("modules_folder", "modules")
        config = utilities.load_json(os.path.sep.join([utilities.get_root_path(), modules_folder_name, "stupid_questions.json"]))
        reddit_client_id = config.get("reddit_client_id")
        reddit_secret = config.get("reddit_secret")

        subreddits = CONFIG_OPTIONS.get("stupid_question_subreddits", ["NoStupidQuestions"])
        try:
            self.reddit = Reddit(client_id=reddit_client_id, client_secret=reddit_secret, user_agent=self.REDDIT_USER_AGENT)
            ## Use a multireddit to pull random post from any of the chosen subreddits
            self.subreddit = self.reddit.subreddit("+".join(subreddits))
        except Exception:
            logger.exception("Unable to create reddit/subreddit instance")

        self.bot.loop.create_task(self.load_questions())


    async def load_questions(self) -> None:
        ## Don't try to pull more data from Reddit if it's already happening
        if (self.is_mid_question_refresh):
            logger.debug("Skipping load_questions as they're already being refreshed.")
            return
        self.is_mid_question_refresh = True

        logger.debug("Loading questions from reddit: top({}), {} submissions".format(
            self.submission_top_time,
            self.submission_count
        ))

        questions = []
        try:
            submission_generator = self.subreddit.top(self.submission_top_time, limit=self.submission_count)
        except Exception:
            logger.exception("Unable to load submission from Reddit.")
            return

        for submission in submission_generator:
            questions.append(submission.title)

        self.last_question_refresh_time = time.time()
        self.questions = questions
        self.is_mid_question_refresh = False

        logger.debug("{} questions loaded at {}".format(len(self.questions), time.asctime()))


    def get_question(self) -> str:
        if (time.time() > self.last_question_refresh_time + self.refresh_time_seconds):
            self.bot.loop.create_task(self.load_questions())

        if (len(self.questions) > 0):
            return random.choice(self.questions)
        return None


    @commands.command(name="stupidquestion", brief="Ask a stupid question, via Reddit.")
    async def stupid_question(self, ctx):
        question = self.get_question()

        if (question):
            await self.hawking.get_audio_player_cog().play_audio(ctx, question, ignore_char_limit=True)
            await ctx.send("Hey <@{}>, {} ```{}```".format(ctx.message.author.id, random.choice(self.THOUGHT_PROVOKING_STRINGS), question))
        else:
            await ctx.send("Sorry <@{}>, but I'm having trouble loading questions from Reddit. Try again in a bit.".format(ctx.message.author.id))


def main():
    return [StupidQuestions, True]
