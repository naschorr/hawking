import logging
import random

from common import utilities
from common import dynamo_manager

from discord.ext import commands
from discord.ext.commands import DefaultHelpCommand, Paginator

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))

class HawkingHelpCommand(commands.DefaultHelpCommand):
    @property
    def max_name_size(self):
        """
        int : Returns the largest name length of the bot's commands.
        """

        size = 0
        try:
            commands = self.context.bot.commands
            if commands:
                size = max(map(lambda c: len(c.name) if self.show_hidden or not c.hidden else 0, commands))
        except AttributeError as e:
            size = 15

        return size + len(CONFIG_OPTIONS.get('activation_str', ''))


    def dump_header_boilerplate(self):
        """
        Adds the header boilerplate text (Description, Version, How to activate) to the paginator
        """
        
        ## Add the description into the help screen
        description = CONFIG_OPTIONS.get("description", [])
        for line in description:
            self.paginator.add_line(line, empty=False)
        if (len(description) > 0):
            self.paginator.add_line()

        ## Append the version info into the help screen
        version = CONFIG_OPTIONS.get("version")
        if (version):
            self.paginator.add_line("Hawking version: {}".format(version), empty=True)

        ## Append (additional) activation note
        activation_note = "Activate with the '{0}' character (ex. '{0}help')".format(self.clean_prefix)
        self.paginator.add_line(activation_note, empty=True)


    def dump_footer_boilerplate(self, categories):
        """
        Adds the footer boilerplate text (Using the help interface) to the paginator
        """
        # Ending note logic from HelpFormatter.format
        command_name = self.context.invoked_with
        ending_note = "Check out the other phrase categories! Why not try '{0}{1} {2}'?".format(
            self.clean_prefix,
            command_name,
            random.choice(categories)
        )
        self.paginator.add_line(ending_note)


    def dump_commands(self):
        """
        Adds information about the bot's available commands (unrelated to the phrase commands) to the paginator
        """
        self.paginator.add_line("Basic Commands:")
        for command in sorted(self.context.bot.commands, key=lambda cmd: cmd.name):
            if((command.module != "phrases" or command.name == 'random' or command.name == 'find') and not command.hidden):
                entry = '  {0}{1:<{width}} {2}'.format(
                    CONFIG_OPTIONS.get('activation_str', ''),
                    command.name,
                    command.short_doc,
                    width=self.max_name_size
                )
                self.paginator.add_line(self.shorten_text(entry))
        self.paginator.add_line()


    def dump_phrase_group(self, phrase_group, width=None):
        """
        Adds information about the supplied phrase group (Group name, tabbed list of phrase commands) to the paginator
        """
        if(not width):
            width = self.max_name_size

        self.paginator.add_line(phrase_group.name + ":")
        for name, phrase in sorted(phrase_group.phrases.items(), key=lambda tup: tup[0]):
            entry = '  {0}{1:<{width}} {2}'.format(
                CONFIG_OPTIONS.get('activation_str', ''),
                name,
                phrase.kwargs.get("help"),
                width=width
            )
            self.paginator.add_line(self.shorten_text(entry))
        self.paginator.add_line()


    def dump_phrase_categories(self, phrase_groups, width=None):
        """
        Adds information about the bot's phrase categories, that the user can drill down into with the help interface,
        to the paginator
        """
        if(not width):
            width = self.max_name_size

        help_string = '{}help '.format(CONFIG_OPTIONS.get('activation_str', ''))
        width += len(help_string)

        self.paginator.add_line('Phrase Category Help:')
        for name, group in sorted(phrase_groups.items(), key=lambda tup: tup[0]):
            ## Don't insert empty groups
            if(len(group.phrases) > 0):
                entry = '  {0}{1:<{width}} {2}'.format(
                    help_string,
                    group.key,
                    group.description,
                    width=width
                )
                self.paginator.add_line(self.shorten_text(entry))
        self.paginator.add_line()


    async def send_phrase_category_help(self, command):
        '''Sends help information for a given command representing a phrase Category'''

        ## Initial setup
        max_width = self.max_name_size
        phrase_groups = self.context.bot.get_cog("Phrases").phrase_groups

        self.dump_header_boilerplate()
        # self.dump_commands()
        self.dump_phrase_group(phrase_groups[command.name], max_width)
        self.dump_phrase_categories(phrase_groups, max_width)
        self.dump_footer_boilerplate(list(phrase_groups.keys()))
        
        self.paginator.close_page()
        await self.send_pages()


    async def send_bot_help(self, mapping):
        '''The main bot help command (overridden)'''

        ## Initial setup
        self.paginator = Paginator()
        phrase_cog = self.context.bot.get_cog("Phrases")
        phrase_groups = None
        if (phrase_cog != None):
            phrase_groups = phrase_cog.phrase_groups

        self.dump_header_boilerplate()
        self.paginator.close_page()

        ## Dump the non-phrase commands
        self.dump_commands()
        self.paginator.close_page()

        ## Dump the base phrase commands
        if (phrase_groups != None):
            phrases_group = phrase_groups["phrases"]
            if(phrases_group):
                self.dump_phrase_group(phrases_group)

            ## Dump the names of the additional phrases. Don't print their commands because that's too much info.
            ## This is a help interface, not a CVS receipt
            self.dump_phrase_categories(phrase_groups)

            self.dump_footer_boilerplate(list(phrase_groups.keys()))

        self.paginator.close_page()
        await self.send_pages()


    async def send_command_help(self, command):
        '''Help interface for the commands themselves (Overridden)'''

        ## Initial setup
        self.paginator = Paginator()
        phrase_groups = self.context.bot.get_cog("Phrases").phrase_groups

        ## Is the help command a category? If so only dump the relv
        command_str = command.__str__()
        if(command.name in phrase_groups):
            await self.send_phrase_category_help(command)
            return

        # <signature> section
        signature = self.get_command_signature(command)
        self.paginator.add_line(signature, empty=True)

        # <long doc> section
        help_section = command.help
        if help_section:
            if(len(help_section) > self.paginator.max_size):
                for line in help_section.splitlines():
                    self.paginator.add_line(line)
            else:
                self.paginator.add_line(help_section, empty=True)

        self.paginator.close_page()
        await self.send_pages()
