import re
import math

import utilities
from discord.ext import commands

## Config
CONFIG_OPTIONS = utilities.load_config()


class Note:
    def __init__(self, beat_length, duration, sub_notes, note, sharp=False, octave=4):
        self.beat_length = beat_length
        self.duration = duration
        self.sub_notes = sub_notes
        self.note = note
        self.sharp = sharp
        self.octave = octave


    def __str__(self):
        return "{}{}{} {}*{}".format(
            self.note,
            self.sharp or "",
            self.octave,
            self.beat_length,
            self.duration
        )


class MusicParser:
    ## Config
    INVALID_CHARS = ["|", ","]
    

    def __init__(self, notes, beat_length=0.25, octave=4):
        self.beat_length = beat_length
        self.octave = octave
        self.notes_preparsed = self._notes_preparser(notes)

        self.notes = []
        for note in self.notes_preparsed:
            parsed = self._parse_note(note)
            if(parsed):
                self.notes.append(parsed)

    ## Methods

    def _notes_preparser(self, notes):
        ## Remove any invalid characters (usually used for formatting)
        for char in self.INVALID_CHARS:
            notes = notes.replace(char, "")

        ## Convert to a list of notes sans whitespace
        notes_list = " ".join(notes.split()).split()

        return notes_list


    def _parse_note(self, note):
        ## Todo: fsm?
        match = re.match(r"^(?:(\d)|([a-z#]+))?([a-z])(#)?(\d)?$", note.strip().lower())

        if(not match):
            return None

        beat_length = self.beat_length
        duration = float(match.group(1) or 1)
        sub_notes = None #parse_sub_notes(list(match.group(2) or ""))
        note = match.group(3)
        sharp = True if match.group(4) else False
        octave = int(match.group(5) or self.octave)

        return Note(beat_length, duration, sub_notes, note, sharp, octave)


class Music:
    ## Keys
    BPM_KEY = "bpm"
    OCTAVE_KEY = "octave"

    ## Defaults
    BPM = CONFIG_OPTIONS.get(BPM_KEY, 100)
    OCTAVE = CONFIG_OPTIONS.get(OCTAVE_KEY, 2)

    ## Config
    ## todo: fix this
    NOTES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]
    HALF_STEPS = len(NOTES)
    OCTAVES = 10
    NOTE_REPLACEMENT = "[laa<{},{}>]"
    REST = "r"
    REST_REPLACEMENT = "[_<{},{}>]"
    SHARP = "#"


    def __init__(self, bot, speech_cog_name="Speech", **kwargs):
        self.bot = bot
        self.speech_cog = self.bot.get_cog(speech_cog_name)

        self.bpm = int(kwargs.get(self.BPM_KEY, self.BPM))
        self.octave = int(kwargs.get(self.OCTAVE_KEY, self.OCTAVE))

        self.pitches = []
        for octave in range(self.OCTAVES):
            self.pitches.append(self._build_pitch_dict(octave))

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
        music_config_regex = r"\\([a-z]+)\s?=\s?(\d+)"
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
    def _build_tts_note_string(self, notes):
        string = ""
        for note in notes:
            note_str = note.note
            if(note.sharp):
                note_str += self.SHARP

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

            string += replacement_str.format(int(note.beat_length * note.duration * 1000), pitch)

        return string

    ## Commands

    @commands.command(pass_context=True, no_pm=True, brief="Sings the given notes aloud!")
    async def music(self, ctx, *, message):
        """Sings the given notes aloud to your voice channel.

        A note can look like any of these:
            'a' - Just the 'a' quarter note in the default second octave.
            '2d' - A 'd' quarter note held for two beats, again in the second octave.
            'c#4' - A 'c#' quarter note in the fourth octave.
            '2b#3' - A 'b#' quarter note held for two beats, in the third octave.
            'r' - A quarter rest.
            '4r' - A quarter rest held for four beats.
        
        Formatting:
            Notes (at the moment) have four distinc parts (Duration?)(Note)(Sharp?)(Octave?).
            Only the base note is necessary, everything else can be omitted if necessary (see above examples)
            A single space NEEDS to be inserted between notes.
            You can also use the | character to help with formatting your bars (ex. 'c d e f | r g a b')

        Inline Configuration:
            BPM:
                The '\\bpm=N' line can be inserted anywhere to adjust the bpm of notes in that line.
                N can be any positive integer. (ex. '\\bpm=120' or '\\bpm=60')
            Octave:
                The '\\octave=N' line can be inserted anywhere to adjust the default octave of notes in that line.
                N can be any integer between 0 and 9 (inclusive) (ex. '\\octave=1' or '\\octave=3'), however 0 through 4 give the best results.

        Examples:
            My Heart Will Go On (first 7 bars):
                '\music \bpm=100 f f f f | e 2f f | e 2f g | 2a 2g | f f f f | e 2f f | 2d 2r'

        Defaults:
            bpm = 100
            octave = 2
        """

        tts_configs, message = self._extract_tts_configs(message)
        music_configs, message = self._extract_music_configs(message)

        self.bpm = music_configs.get(self.BPM_KEY, self.bpm)
        beat_length = 60 / self.bpm  # for a quarter note
        self.octave = music_configs.get(self.OCTAVE_KEY, self.octave)

        notes = MusicParser(message, beat_length, self.octave).notes
        tts_notes = self._build_tts_note_string(notes)

        say = self.speech_cog.say.callback
        await say(self.speech_cog, ctx, message=" ".join(tts_configs) + tts_notes)
