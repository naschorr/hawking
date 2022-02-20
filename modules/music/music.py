import re
import math
import random
import logging
from collections import OrderedDict

from discord.ext import commands

from common import utilities
from common.database import dynamo_manager
from common.module.discoverable_module import DiscoverableCog
from common.module.module_initialization_container import ModuleInitializationContainer

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class Note:
    def __init__(self, beat_length, duration, note, sharp=False, octave=4, sub_notes=[]):
        self.beat_length = beat_length
        self.duration = duration
        self.note = note
        self.sharp = sharp
        self.octave = octave
        self.sub_notes = sub_notes

        self.dynamo_db = dynamo_manager.DynamoManager()


    def __str__(self):
        return "{}{}{} {}*{} [{}]".format(
            self.note,
            self.sharp or "",
            self.octave,
            self.beat_length,
            self.duration,
            ", ".join(self.sub_notes)
        )


class MusicParser:
    ## Config
    INVALID_CHARS = ["|", ","]
    CHAR_REGEX = r"([a-z])"
    INT_REGEX = r"(\d)"
    SHARP_REGEX = r"(#)"
    CATCHALL_REGEX = r"(.?)"
    FRACTIONAL_REGEX = r"(\/)"

    ## Start State Machine Classes

    ## Base state that all other states inherit from
    class BaseState:    # Todo: make virtual
        def __init__(self, exit_dict={}, error_handler=None):
            self.exit_dict = exit_dict
            self.error_handler = error_handler


        ## Try to get the first character of a string
        def emit_char(self, string):
            try:
                return string[0]
            except:
                return ""


        ## Try to get the first character of a string, and return the string that it was emitted from
        def emit_consume_char(self, string):
            try:
                return string[0], string[1:]
            except:
                return "", ""


        ## Unimplemented state enter handler
        def enter(self):
            raise NotImplementedError("State.enter() isn't implemented")


        ## State exit handler
        def exit(self, char, string, **kwargs):
            for regex_string, handler in self.exit_dict.items():
                match = re.match(regex_string, char)
                ## logger.debug("MATCHING {}, {}, {}".format(regex_string, char, handler.__self__.__class__.__name__))
                if(match):
                    return handler(string, **kwargs)

            if(self.error_handler):
                self.error_handler(char, string)
            return None


    ## Initial state
    class StartState(BaseState):
        def enter(self, string, **kwargs):
            char = self.emit_char(string)
            ## logger.debug("Enter {} '{}', {}".format(self.__class__.__name__, string, kwargs))

            return self.exit(char, string, **kwargs)


    ## Duration parsing state
    class DurationState(BaseState):
        def enter(self, string, **kwargs):
            char, consumed_str = self.emit_consume_char(string)
            ## logger.debug("Enter {} '{}' '{}', {}".format(self.__class__.__name__, consumed_str, char, kwargs))

            return self.exit(self.emit_char(consumed_str), consumed_str, duration=int(char), **kwargs)


    ## Note parsing state
    class NoteState(BaseState):
        def enter(self, string, **kwargs):
            char, consumed_str = self.emit_consume_char(string)
            ## logger.debug("Enter {} '{}' '{}', {}".format(self.__class__.__name__, consumed_str, char, kwargs))

            return self.exit(self.emit_char(consumed_str), consumed_str, note=char, **kwargs)


    ## Sharp parsing state
    class SharpState(BaseState):
        def enter(self, string, **kwargs):
            char, consumed_str = self.emit_consume_char(string)
            ## logger.debug("Enter {} '{}' '{}', {}".format(self.__class__.__name__, consumed_str, char, kwargs))

            return self.exit(self.emit_char(consumed_str), consumed_str, sharp=char, **kwargs)


    ## Octave parsing state
    class OctaveState(BaseState):
        def enter(self, string, **kwargs):
            char, consumed_str = self.emit_consume_char(string)
            ## logger.debug("Enter {} '{}' '{}', {}".format(self.__class__.__name__, consumed_str, char, kwargs))

            return self.exit(self.emit_char(consumed_str), consumed_str, octave=int(char), **kwargs)


    ## NoteObj creation state
    class NoteObjState(BaseState):
        def enter(self, string, **kwargs):
            char, consumed_str = self.emit_consume_char(string)
            ## logger.debug("Enter {} '{}' '{}', {}".format(self.__class__.__name__, consumed_str, char, kwargs))

            beat_length = kwargs.get("beat_length", 0.25)
            duration = kwargs.get("duration", 1)
            note = kwargs.get("note")
            assert note is not None
            sharp = kwargs.get("sharp", False)
            octave = kwargs.get("octave", kwargs.get("default_octave", 2))

            note_obj = Note(beat_length, duration, note, sharp, octave, [])

            ## Clean up kwargs for next pass
            kwargs.pop("note_obj", None)
            kwargs.pop("duration", None)
            kwargs.pop("note", None)
            kwargs.pop("sharp", None)
            kwargs.pop("octave", None)

            ## Next state
            return self.exit(char, string, note_obj=note_obj, **kwargs)


    ## SubNote creation state
    class SubNoteState(BaseState):
        def enter(self, string, **kwargs):
            char, consumed_str = self.emit_consume_char(string)
            ## logger.debug("Enter {} '{}' '{}', {}".format(self.__class__.__name__, consumed_str, char, kwargs))

            note_obj = kwargs.get("note_obj")
            assert note_obj is not None
            sub_notes = kwargs.get("sub_notes", [])
            sub_notes.append(note_obj)

            ## Clean up kwargs for next pass
            kwargs.pop("note_obj", None)
            kwargs.pop("sub_notes", None)

            return self.exit(self.emit_char(consumed_str), consumed_str, sub_notes=sub_notes, **kwargs)


    ## Final output state
    class FinalState(BaseState):
        def enter(self, string, **kwargs):
            ## logger.debug("Enter {} '{}', {}".format(self.__class__.__name__, string, kwargs))

            note_obj = kwargs.get("note_obj")
            sub_notes = kwargs.get("sub_notes", [])
            beat_length = kwargs.get("beat_length", 0.25) / (len(sub_notes) + 1)

            if(note_obj):
                for note in sub_notes:
                    note.beat_length = beat_length
                note_obj.beat_length = beat_length

                note_obj.sub_notes = sub_notes
                
            return note_obj


    ## Error handling state
    class ErrorState(BaseState):
        def enter(self, char, string):
            logger.debug("Error in music state machine", char, string)
            return None

    ## End State Machine Classes

    def __init__(self, notes, beat_length=0.25, octave=4):
        self.beat_length = beat_length
        self.octave = octave
        self.notes_preparsed = self._notes_preparser(notes)

        self.parse_note = self._init_state_machine()

        self.notes = []
        for note in self.notes_preparsed:
            parsed = self.parse_note(note.lower(), beat_length=self.beat_length, default_octave=self.octave)
            if(parsed):
                self.notes.append(parsed)

    ## Methods

    ## Initialize the note parsing state machine, returning a callable entry point (start.enter())
    def _init_state_machine(self):
        ## Init error handler state
        error_state_dict = {}
        error_handler = self.ErrorState(error_state_dict, None).enter

        ## Init states
        start_state = self.StartState({}, error_handler)
        duration_state = self.DurationState({}, error_handler)
        note_state = self.NoteState({}, error_handler)
        sharp_state = self.SharpState({}, error_handler)
        octave_state = self.OctaveState({}, error_handler)
        note_obj_state = self.NoteObjState({}, error_handler)
        sub_note_state = self.SubNoteState({}, error_handler)
        final_state = self.FinalState({}, error_handler)

        ## Populate state exit_dicts
        start_state.exit_dict = OrderedDict([(self.INT_REGEX, duration_state.enter),
                                             (self.CHAR_REGEX, note_state.enter),
                                             (self.CATCHALL_REGEX, final_state.enter)])
        duration_state.exit_dict = OrderedDict([(self.CHAR_REGEX, note_state.enter)])
        note_state.exit_dict = OrderedDict([(self.SHARP_REGEX, sharp_state.enter),
                                            (self.INT_REGEX, octave_state.enter),
                                            (self.CATCHALL_REGEX, note_obj_state.enter)])
        sharp_state.exit_dict = OrderedDict([(self.INT_REGEX, octave_state.enter),
                                             (self.CATCHALL_REGEX, note_obj_state.enter)])
        octave_state.exit_dict = OrderedDict([(self.CATCHALL_REGEX, note_obj_state.enter)])
        note_obj_state.exit_dict = OrderedDict([(self.FRACTIONAL_REGEX, sub_note_state.enter),
                                                (self.CATCHALL_REGEX, final_state.enter)])
        sub_note_state.exit_dict = OrderedDict([(self.CATCHALL_REGEX, start_state.enter)])

        ## Return an entry point into the fsm
        return start_state.enter


    def _notes_preparser(self, notes):
        ## Remove any invalid characters (usually used for formatting)
        for char in self.INVALID_CHARS:
            notes = notes.replace(char, "")

        ## Convert to a list of notes sans whitespace
        notes_list = " ".join(notes.split()).split()

        return notes_list


class Music(DiscoverableCog):
    '''
    Note that there's something wrong with the note parsing logic. It still works, but it takes waaay too long now. I'll
    look into it later.
    '''

    ## Keys
    BPM_KEY = "bpm"
    OCTAVE_KEY = "octave"
    TONE_KEY = "tone"
    BAD_KEY = "bad"
    BAD_PERCENT_KEY = "bad_percent"

    ## Defaults
    BPM = CONFIG_OPTIONS.get(BPM_KEY, 100)
    OCTAVE = CONFIG_OPTIONS.get(OCTAVE_KEY, 2)
    TONE = CONFIG_OPTIONS.get(TONE_KEY, False)
    BAD = CONFIG_OPTIONS.get(BAD_KEY, False)
    BAD_PERCENT = CONFIG_OPTIONS.get(BAD_PERCENT_KEY, 10)

    ## Config
    ## todo: fix this
    NOTES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]
    HALF_STEPS = len(NOTES)
    OCTAVES = 10
    NOTE_REPLACEMENT = "[laa<{},{}>]"
    REST = "r"
    REST_REPLACEMENT = "[_<{},{}>]"
    TONE_REPLACEMENT = "[:t <{},{}>]"
    SHARP = "#"


    def __init__(self, hawking, bot, **kwargs):
        super().__init__(*args, **kwargs)

        self.hawking = hawking
        self.bot = bot

        self.bpm = int(kwargs.get(self.BPM_KEY, self.BPM))
        self.octave = int(kwargs.get(self.OCTAVE_KEY, self.OCTAVE))
        self.tone = kwargs.get(self.TONE_KEY, self.TONE)
        self.bad = kwargs.get(self.BAD_KEY, self.BAD)
        self.bad_percent = int(kwargs.get(self.BAD_PERCENT_KEY, self.BAD_PERCENT))

        self.pitches = []
        for octave in range(self.OCTAVES):
            self.pitches.append(self._build_pitch_dict(octave))

    ## Properties

    @property
    def audio_player_cog(self):
        return self.hawking.get_audio_player_cog()

    ## Methods

    ## Calculates the frequency of a note at a given number of half steps from the reference frequency
    def _get_frequency(self, half_steps, reference=440):
        a = 1.059463
        frequency = int(reference * pow(a, half_steps))

        return frequency


    ## Builds a dictionary of notes and their pitches at a given octave
    def _build_pitch_dict(self, octave):
        reference_frequency = 440   # A
        reference_octave = 4
        refence_steps_from_c4 = 9
        reference_steps_from_c0 = self.HALF_STEPS * reference_octave + refence_steps_from_c4

        pitch_dict = {}
        for index, note in enumerate(self.NOTES):
            half_steps = octave * self.HALF_STEPS + index
            pitch_dict[note] = self._get_frequency(half_steps - reference_steps_from_c0,
                                                   reference_frequency)

        return pitch_dict


    ## Pulls any TTS config options (ex. [:dv hs 10]) from the message string
    def _extract_tts_configs(self, string):
        tts_config_regex = r"(\[:.+?\])"
        tts_configs = []

        tts_config = re.search(tts_config_regex, string)
        while(tts_config):
            tts_configs.append(tts_config.group(1))
            string = string[:tts_config.start()] + string[tts_config.end():]
            tts_config = re.search(tts_config_regex, string)

        return tts_configs, string


    ## Pulls any music config options (ex. \bpm=N) from the message string
    def _extract_music_configs(self, string):
        music_config_regex = r"\\([a-z_]+)\s?=\s?(\d+)"
        music_configs = {}

        music_config = re.search(music_config_regex, string)
        while(music_config):
            key = music_config.group(1)
            value = int(music_config.group(2))
            music_configs[key] = value

            string = string[:music_config.start()] + string[music_config.end():]
            music_config = re.search(music_config_regex, string)

        return music_configs, string


    ## Turns a list of Note objects into a string of TTS friendly phonemes
    def _build_tts_note_string(self, notes, **configs):
        use_tones = configs.get(self.TONE_KEY, self.tone)
        use_bad = configs.get(self.BAD_KEY, self.bad)
        bad_percent = configs.get(self.BAD_PERCENT_KEY, self.bad_percent)

        string = ""
        note_index = 0
        for note in notes:
            ## Push any sub_notes into their appropriate position in the notes list
            sub_note_index = 0
            for sub_note in note.sub_notes:
                notes.insert(note_index + 1 + sub_note_index, sub_note)
                sub_note_index += 1

            ## Create a textual representation of the note
            note_str = note.note
            if(note.sharp):
                note_str += self.SHARP

            ## Select a format string for the type of note
            if(note_str in self.NOTES):
                replacement_str = self.NOTE_REPLACEMENT
                try:
                    pitch = self.pitches[note.octave][note_str]
                except IndexError:
                    continue
            elif(note_str == self.REST):
                replacement_str = self.REST_REPLACEMENT
                pitch = 10  # Arbitrary low pitch
            else:
                continue

            ## Assign a duration of time to hold the note for
            duration = note.duration

            ## Randomize the note's pitch and duration if use_bad is True
            if(use_bad):
                pitch_offset_max = pitch * (bad_percent / 100)
                pitch += random.uniform(-pitch_offset_max, pitch_offset_max)
                duration_offset_max = duration * (bad_percent / 100)
                duration += random.uniform(-duration_offset_max, duration_offset_max)

            ## Create the TTS friendly string for the note, and use the tone format string if necessary
            if(use_tones):
                string += self.TONE_REPLACEMENT.format(int(pitch), int(note.beat_length * duration * 1000))
            else:
                string += replacement_str.format(int(note.beat_length * duration * 1000), int(pitch))
            note_index += 1

        return string

    ## Commands

    @commands.command(no_pm=True, brief="Sings the given notes aloud!")
    async def music(self, ctx, notes, ignore_char_limit=False):
        """
        Sings the given notes aloud to your voice channel.

        A note (or notes) can look like any of these:
            'a' - Just the 'a' quarter note in the default second octave.
            '2d' - A 'd' quarter note held for two beats, again in the second octave.
            'c#4' - A 'c#' quarter note in the fourth octave.
            '2b#3' - A 'b#' quarter note held for two beats, in the third octave.
            'r' - A quarter rest.
            '4r' - A quarter rest held for four beats.
            'b/b' - Two 'b' eighth notes.
            '2c#/d#/a3/f' - A 'c#' sixteenth note held for two beats, a 'd#' sixteenth note,
                an 'a' sixteenth note in the third octave, and a 'f' sixteenth note.
        
        Formatting:
            Notes (at the moment) have four distinct parts (Duration?)(Note)(Sharp?)(Octave?).
            Only the base note is necessary, everything else can be omitted if necessary
                (see examples) A single space NEEDS to be inserted between notes.
            You can chain notes together by inserting a '/' between notes, this lets you create
                multiple shorter beats.
            This lets you approximate eighth notes, sixteenth notes, thirty-second notes, and
                really any other division of notes. (Twelfth, Twentieth, etc)
            You can also use the | character to help with formatting your bars
                (ex. 'c d e f | r g a b')

        Inline Configuration:
            BPM:
                The '\\bpm=N' line can be inserted anywhere to adjust the bpm of notes in that
                line. N can be any positive integer. (ex. '\\bpm=120' or '\\bpm=60')
            Octave:
                The '\\octave=N' line can be inserted anywhere to adjust the default octave of
                notes in that line. N can be any integer between 0 and 9 (inclusive)
                (ex. '\\octave=1' or '\\octave=3'), however 0 through 4 give the best results.
            Tones:
                The '\\tone=N' line can be inserted anywhere to set whether or not to use tones
                instead of phonemes on that line. N can be either 0 or 1, where 0 disables tones,
                and 1 enables them.
            Bad:
                The '\\bad=N' line can be inserted anywhere to set whether or not to make the notes
                on that line sound worse (See: https://www.youtube.com/watch?v=KolfEhV-KiA). N can
                be either 0 or 1, where 0 disables the badness, and 1 enables it.
            Bad_Percent:
                The '\\bad_percent=N' line can be inserted anywhere to set the level of badness, 
                when using the \\bad config. N can be any positive integer. It works as a
                percentage where if N = 0, then it's not at all worse, and N = 100 would be 100%
                worse. Needs \\bad to be set to have any effect.

        Examples:
            My Heart Will Go On (first 7 bars):
                '\music \\bpm=100 f f f f | e 2f f | e 2f g | 2a 2g | f f f f | e 2f f | 2d 2r'

            Sandstorm (kinda):
                '\music \\bpm=136 \\octave=3 \\tone=1 b/b/b/b/b b/b/b/b/b/b/b e/e/e/e/e/e/e
                    d/d/d/d/d/d/d a b/b/b/b/b/b b/b/b/b/b/b c# b/b/b/b/b/a'

        Defaults:
            bpm = 100
            octave = 2
            tone = 0
            bad = 0
            bad_percent = 10
        """

        ## Todo: preserve the position of tts_configs in the message
        tts_configs, message = self._extract_tts_configs(notes)
        music_configs, message = self._extract_music_configs(notes)

        bpm = music_configs.get(self.BPM_KEY, self.bpm)
        beat_length = 60 / bpm  # for a quarter note
        octave = music_configs.get(self.OCTAVE_KEY, self.octave)

        notes = MusicParser(message, beat_length, octave).notes
        tts_notes = self._build_tts_note_string(notes, **music_configs)

        await self.speech_cog._say(ctx, " ".join(tts_configs) + tts_notes, ignore_char_limit=ignore_char_limit)


def main() -> ModuleInitializationContainer:
    ## return ModuleInitializationContainer(Music)
    return False
