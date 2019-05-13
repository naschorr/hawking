import os

import discord
from discord.ext import commands
from praw import Reddit

import utilities

## Config
CONFIG_OPTIONS = utilities.load_config()

class StupidQuestions:
    REDDIT_USER_AGENT = "discord:hawking:{} (by /u/hawking-py)".format(CONFIG_OPTIONS.get("version", "0.0.1"))

    def __init__(self, hawking, bot, *args, **kwargs):
        self.hawking = hawking
        self.bot = bot

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
        except Exception as e:
            utilities.debug_log("Unable to create reddit/subreddit instance,", e, debug_level=1)
        
    def get_question(self):
        try:
            submission = self.subreddit.random()
        except Exception as e:
            utilities.debug_log("Unable to load submission from Reddit.", e, debug_level=2)
            return None

        return submission.title

    @commands.command(pass_context=True, no_pm=True, name="stupidquestion", brief="Ask a stupid question, via Reddit.")
    async def stupid_question(self, ctx):
        question = self.get_question()
        if (question):
            speech_cog = self.hawking.get_speech_cog()
            await speech_cog.say.callback(speech_cog, ctx, message=question)
        else:
            await self.bot.say("Sorry <@{}>, but I'm having trouble loading questions from Reddit. Try again in a bit.".format(ctx.message.author.id))


def main():
    return [StupidQuestions, True]
