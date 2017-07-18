import json
from discord.ext import commands


class Phrase:
    def __init__(self, name, message, **kwargs):
        self.name = name
        self.message = message
        self.kwargs = kwargs


class Phrases:
    ## Keys
    PHRASES_KEY = "phrases"
    NAME_KEY = "name"
    MESSAGE_KEY = "message"
    HELP_KEY = "help"
    BRIEF_KEY = "brief"
    DESCRIPTION_KEY = "description"


    def __init__(self, bot, phrases_json_path, speech_cog_name="Speech", **command_kwargs):
        self.bot = bot
        self.phrases_json_path = phrases_json_path
        self.speech_cog = self.bot.get_cog(speech_cog_name)
        self.command_kwargs = command_kwargs
        self.command_names = []

        ## Make sure context is always passed to the callbacks
        self.command_kwargs["pass_context"] = True

        ## Load and add the phrases
        self.init_phrases()


    ## Initialize the phrases available to the bot
    def init_phrases(self):
        counter = 0
        for phrase in self.load_phrases(self.phrases_json_path):
            try:
                self.add_phrase(phrase)
            except TypeError as e:
                print(e, "Skipping...")
            else:
                counter += 1

        print("Loaded {} phrases.".format(counter))
        return counter


    ## Unloads all phrase commands, then reloads them from the phrases.json file
    def reload_phrases(self):
        self.remove_phrases()
        return self.init_phrases()


    ## Load phrases from json into a list of phrase objects
    def load_phrases(self, path):
        ## Insert source[key] (if it exists) into target[key], else insert a default string
        def insert_if_exists(target, source, key, default=None):
            if(key in source):
                target[key] = source[key]
            return target

        phrases = []
        with open(path) as fd:
            for phrase_raw in json.load(fd)[self.PHRASES_KEY]:
                try:
                    ## Todo: make this less ugly
                    kwargs = {}
                    help_value = phrase_raw.get(self.HELP_KEY)  # fallback for the help submenus
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.HELP_KEY)
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.BRIEF_KEY, help_value)
                    kwargs = insert_if_exists(kwargs, phrase_raw, self.DESCRIPTION_KEY, help_value)

                    phrase_name = phrase_raw[self.NAME_KEY]
                    phrase = Phrase(
                        phrase_name,
                        phrase_raw[self.MESSAGE_KEY],
                        **kwargs
                    )
                    phrases.append(phrase)
                    self.command_names.append(phrase_name)
                except Exception as e:
                    print("Exception", e, "when loading phases.json. Skipping...")

        return phrases


    ## Unloads the preset phrases from the bot's command list
    def remove_phrases(self):
        for name in self.command_names:
            self.bot.remove_command(name)

        return True


    ## Add a phrase command to the bot's command list
    def add_phrase(self, phrase):
        if(not isinstance(phrase, Phrase)):
            raise TypeError("{} not instance of Phrase.".format(phrase))

        ## Manually build command to be added
        command = commands.Command(
            phrase.name,
            self._create_phrase_callback(phrase.message),
            **phrase.kwargs,
            **self.command_kwargs
        )
        ## _phrase_callback doesn't have an instance linked to it, 
        ## (not technically a method of Phrases?) so manually insert the correct instance anyway.
        ## This fixes the broken category label in the help page.
        command.instance = self

        self.bot.add_command(command)


    ## Build a dynamic callback to invoke the bot's say method
    def _create_phrase_callback(self, message):
        ## Pass a self arg to it now that the command.instance is set to self
        async def _phrase_callback(self, ctx):
            say = self.speech_cog.say.callback
            await say(self.speech_cog, ctx, message=message)

        return _phrase_callback
