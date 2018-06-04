import itertools
import inspect

from discord.ext.commands.formatter import HelpFormatter, Paginator
from discord.ext.commands.core import Command

import utilities
import dynamo_helper

## Config
CONFIG_OPTIONS = utilities.load_config()


class HawkingHelpFormatter(HelpFormatter):
    @property
    def max_name_size(self):
        """
        int : Returns the largest name length of the bot's commands.
        """
        try:
            commands = self.context.bot.commands
            if commands:
                return max(map(lambda c: len(c.name) if self.show_hidden or not c.hidden else 0, commands.values()))
            return 0
        except AttributeError:
            return len(self.command.name)

    def dump_header_boilerplate(self):
        """
        Adds the header boilerplate text (Description, Version, How to activate) to the paginator
        """
        self._paginator.add_line(CONFIG_OPTIONS.get("description"), empty=False)

        ## Append the version info into the help screen
        version_note = "Hawking version: {}".format(CONFIG_OPTIONS.get("version", "Beta"))
        self._paginator.add_line(version_note, empty=True)

        ## Append (additional) activation note
        activation_note = "Activate with the '{0}' character (ex. '{0}help')".format(self.clean_prefix)
        self._paginator.add_line(activation_note, empty=True)

    def dump_footer_boilerplate(self):
        """
        Adds the footer boilerplate text (Using the help interface) to the paginator
        """
        # Ending note logic from HelpFormatter.format
        command_name = self.context.invoked_with
        ending_note = "Type '{0}{1}' command for more info on a command.\n" \
                        "You can also type '{0}{1}' category for more info on a category.".format(
                            self.clean_prefix, command_name)
        self._paginator.add_line(ending_note)

    def dump_commands(self):
        """
        Adds information about the bot's available commands (unrelated to the phrase commands) to the paginator
        """
        self._paginator.add_line("Commands:")
        for name, command in sorted(self.context.bot.commands.items(), key=lambda tup: tup[1].module.__name__):
            module_name = command.module.__name__
            if(module_name != "phrases" and not command.hidden):
                entry = '  {0:<{width}} {1}'.format(name, command.short_doc, width=self.max_name_size)
                self._paginator.add_line(self.shorten(entry))
        self._paginator.add_line()

    def dump_phrase_group(self, phrase_group, width=None):
        """
        Adds information about the supplied phrase group (Group name, tabbed list of phrase commands) to the paginator
        """
        if(not width):
            width = self.max_name_size

        self._paginator.add_line(phrase_group.name + ":")
        for name, phrase in sorted(phrase_group.phrases.items(), key=lambda tup: tup[0]):
            entry = '  {0:<{width}} {1}'.format(name, phrase.kwargs.get("help"), width=width)
            self._paginator.add_line(self.shorten(entry))
        self._paginator.add_line()

    def dump_phrase_categories(self, phrase_groups, width=None):
        """
        Adds information about the bot's phrase categories, that the user can drill down into with the help interface,
        to the paginator
        """
        if(not width):
            width = self.max_name_size

        header_raw = "Phrase Categories (Use '{}help category' to see the category's extra commands!):"
        self._paginator.add_line(header_raw.format(self.clean_prefix))
        for name, group in sorted(phrase_groups.items(), key=lambda tup: tup[0]):
            ## Don't insert empty groups
            if(len(group.phrases) > 0):
                entry = '  {0:<{width}} {1}'.format(group.key, group.description, width=width)
                self._paginator.add_line(self.shorten(entry))
        self._paginator.add_line()

    ## Override default formatting method
    def format(self):
        def category(tup):
            cog = tup[1].cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ':' if cog is not None else '\u200bNo Category:'

        ## Initial setup
        max_width = self.max_name_size
        self._paginator = Paginator()
        phrase_groups = self.context.bot.get_cog("Phrases").phrase_groups

        ## Handle help for subcommands (ex. \help say, \help random, etc)
        if isinstance(self.command, Command):
            command_str = self.command.__str__()
            if(command_str in phrase_groups):
                self.dump_header_boilerplate()
                self.dump_commands()
                self.dump_phrase_group(phrase_groups[command_str], max_width)
                self.dump_phrase_categories(phrase_groups, max_width)
                self.dump_footer_boilerplate()
                return self._paginator.pages

            # <signature portion>
            signature = self.get_command_signature()
            self._paginator.add_line(signature, empty=True)

            # <long doc> section
            help_section = self.command.help
            if help_section:
                if(len(help_section) > self._paginator.max_size):
                    for line in help_section.splitlines():
                        self._paginator.add_line(line)
                else:
                    self._paginator.add_line(help_section, empty=True)

            # end it here if it's just a regular command
            if not self.has_subcommands():
                self._paginator.close_page()
                return self._paginator.pages

        self.dump_header_boilerplate()

        ## Dump the non-phrase commands
        self.dump_commands()

        ## Dump the base phrase commands
        phrases_group = phrase_groups["phrases"]
        if(phrases_group):
            self.dump_phrase_group(phrases_group)

        ## Dump the names of the additional phrases. Don't print their commands because that's too much info.
        ## This is a help interface, not a CVS receipt
        self.dump_phrase_categories(phrase_groups)

        self.dump_footer_boilerplate()

        return self._paginator.pages
