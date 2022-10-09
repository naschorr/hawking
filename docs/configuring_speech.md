# Speech Configuration with Hawking

Speech is modified with the same inline commands seen in Moonbase Alpha. They generally follow the pattern of `[:(command)(parameter)]`, where the open bracket colon starts a command, `(command)` selects a specific command, and  `(parameter)` configures it. Some commands can be chained together, inside of a single set of brackets. Most commands can also be shortened down to a single letter, too.

## Changing Hawking's voice

Select a preset voice with the `[:name(n)]` command, where `(n)` is one of:
- `betty`
- `dennis`
- `frank`
- `harry`
- `kit`
- `paul` (this is the default voice)
- `rita`
- `ursula`
- `wendy`

You can also shorten the command to just `[:n(n)]` where `(n)` is the first letter of the name you want to use. For example: `[:nf]`.

## Changing how fast Hawking speaks

The rate of speech can be changed with `[:rate(r)]`, where `(r)` is the words per minute to speak. The default is 200, and must be between 75 and 600. For example, `[:rate100]` will cause all future speech to be spoken at 100 words per minute, which is half of the default.

## Playing tones and dialing phones

Tones are pure noise, simply a sound over a duration. They're usually used to simulate of beeps and boops. They follow the form `[:tone(f),(l)]`, where `(f)` is the frequency of the tone, and `(l)` is the length of the tone in milliseconds. For example, `[:tone100,2000]` will generate a 100 hertz tone for 2 seconds, and `[:tone750,150]` will generate a beep at 750 hertz over 150 milliseconds.

Similar to tones is the dial command, which can be used to emulate the touch tones used when dialing a phone number (see the `/phrase pizza` command). It takes the form `[:dial(n)]`, where `(n)` is the number to dial, though it can take any arbitrary amount of digits. For example, `[:dial8675309]` would generate the dial tone for the phone number "867-5309".

## Phonemes

Phonemes are the building blocks of more complex sounds, as they give you greater control over how Hawking generates the sounds that make up speech. They follow the pattern of: `[(phonemes)<(d),(p)>]`, where `(phonemes)` is one or more phonemes from the table below, `(d)` is the duration in milliseconds that it takes to speak each phoneme, and `(p)` is the pitch number (see the second table in this section) that the phoneme should end on. Additionally, multiple groups of phonemes and their respective duration and pitch can be chained together as well. Similarly, phonemes (and groups of phonemes) don't technically need a duration and pitch number added to them either.

Below is a table that shows each phoneme with their respective sounds. Bolded letters indicate the exact sound each phoneme makes. For example, the phoneme `aa` makes the `o` sound in the word "pot".

| Phoneme   | Sound         | ㅤㅤ | Phoneme   | Sound         | ㅤㅤ | Phoneme   | Sound
| - | - | - | - | - | - | - | - |
| _         | *silence*     | ㅤㅤ | hx        | **h**at       | ㅤㅤ | r         | **r**ope
| q         | *full stop*   | ㅤㅤ | ih        | p**i**t       | ㅤㅤ | rr        | anoth**er**
| aa        | p**o**t       | ㅤㅤ | ir        | p**ee**r      | ㅤㅤ | rx        | fi**r**e
| ae        | p**a**t       | ㅤㅤ | iy        | b**ea**n      | ㅤㅤ | s         | **s**ap
| ar        | b**ar**n      | ㅤㅤ | jh        | **j**eep      | ㅤㅤ | sh        | **sh**eep
| aw        | br**ow**      | ㅤㅤ | k         | **c**andle    | ㅤㅤ | zh        | mea**s**ure
| ax        | **a**bout     | ㅤㅤ | el        | dang**l**e    | ㅤㅤ | t         | **t**ack
| ay        | b**uy**       | ㅤㅤ | l         | **l**ad       | ㅤㅤ | th        | **th**ick
| ey        | b**ay**       | ㅤㅤ | lx        | unti**l**     | ㅤㅤ | dh        | **th**en
| er        | p**ai**r      | ㅤㅤ | m         | **m**ad       | ㅤㅤ | df        | wri**t**er
| b         | **b**atch     | ㅤㅤ | en        | garde**n**    | ㅤㅤ | tx        | ba**tt**en
| ch        | **ch**eap     | ㅤㅤ | n         | **n**ature    | ㅤㅤ | uw        | b**oo**n
| d         | **d**ad       | ㅤㅤ | nx        | ba**ng**      | ㅤㅤ | uh        | p**u**t
| dx        | un**d**er     | ㅤㅤ | ao        | b**ou**ght    | ㅤㅤ | ah        | p**u**tt
| dz        | wi**d**th     | ㅤㅤ | or        | t**o**rn      | ㅤㅤ | v         | **v**at
| eh        | p**e**t       | ㅤㅤ | ur        | p**oo**r      | ㅤㅤ | w         | **w**hy
| ix        | kiss**e**s    | ㅤㅤ | ow        | n**o**        | ㅤㅤ | yu        | c**u**te
| f         | **f**at       | ㅤㅤ | oy        | b**oy**       | ㅤㅤ | yx        | **y**ank
| g         | **g**ame      | ㅤㅤ | p         | **p**at       | ㅤㅤ | z         | **z**ap

Here's a pitch table that correlates pitches to pitch numbers, and their respective musical note.

| Note  | Pitch (Hz)    | Pitch Number  | ㅤㅤ | Note   | Pitch (Hz)    | Pitch Number
| - | - | - | - | - | - | - |
| C2    | 65            | 1             | ㅤㅤ | G      | 196           | 20
| C#    | 69            | 2             | ㅤㅤ | G#     | 207           | 21
| D     | 73            | 3             | ㅤㅤ | A      | 220           | 22
| D#    | 77            | 4             | ㅤㅤ | A#     | 233           | 23
| E     | 82            | 5             | ㅤㅤ | B      | 247           | 24
| F     | 87            | 6             | ㅤㅤ | C4     | 261           | 25
| F#    | 92            | 7             | ㅤㅤ | C#     | 277           | 26
| G     | 98            | 8             | ㅤㅤ | D      | 293           | 27
| G#    | 103           | 9             | ㅤㅤ | D#     | 311           | 28
| A     | 110           | 10            | ㅤㅤ | E      | 329           | 29
| A#    | 116           | 11            | ㅤㅤ | F      | 348           | 30
| B     | 123           | 12            | ㅤㅤ | F#     | 370           | 31
| C3    | 130           | 13            | ㅤㅤ | G      | 392           | 32
| C#    | 138           | 14            | ㅤㅤ | G#     | 415           | 33
| D     | 146           | 15            | ㅤㅤ | A      | 440           | 34
| D#    | 155           | 16            | ㅤㅤ | A#     | 466           | 35
| E     | 164           | 17            | ㅤㅤ | B      | 494           | 36
| F     | 174           | 18            | ㅤㅤ | C5     | 523           | 37
| F#    | 185           | 19

That's a lot of data to throw at you, so check out these examples to get a feel for it:

- Speaks "complicated", without any duration or pitch numbers specified: `[kaamplihkeytxehd]`
- Speaks "hello" over the span of 600ms at pitch number 3: `[hx<100,3>eh<100,3>l<200,3>ow<200,3>]`
- Speaks "daa" for a second, ending at pitch number 1, pauses for a second, ending at pitch number 30, then speaks "daa" for a second, starting at pitch number 30 and ending back at pitch number 1: `[daa<1000,1>_<1000,30>daa<1000,1>]`

## Advanced customization

Customize the sound of the voice with `[:dv (commands)]`. This requires additional subcommands to fine-tune your desired behavior. Below are the more common/noticeable ones:

- Pitch can be changed with `ap (p)` where `(p)` is the average pitch in hertz.
- Change the size of the speaker\'s head with `hs (s)` where `(s)` is the amount of change in percentage. For example, `50` would represent a halved head size. Defaults to `100`.
- Gender can be changed with `sx (g)` where `(g)` is `0` for female, or `1` for male.
- Breathiness can be changed with `br (b)` where `(b)` is the amount of breathiness added in decibels. Default to `0`.
- Smoothness can be changed with `sm (s)` where `(s)` adjusts how smooth the voice sounds as a percentage. Defaults to `30`.
- Richness can be changed with `ri (r)`, where `(r)` is the amount of change in percentage. Defaults to `70`.

Note that the `[:dv]` command can support multiple subcommands, each one separated by a space. Also note that you can't have the subcommand next to its parameter, they must have a space between them. Check out these examples to get a feel for it:

- Set the average pitch to 15 hertz: `[:dv ap 15]`
- Increase the head size by 50%, and set the average pitch to 10 hertz: `[:dv hs 150 ap 10]`
- Set the gender to female, the averate pitch to 200 hertz, and half the head size: `[:dv sx 0 ap 200 hs 50]`
- Set the average pitch to 20 hertz, make the voice as un-smooth as possible, and 90% richness: `[:dv ap 20 sm 0 ri 90]`

## Examples

- Use the "Harry" voice: `/say [:name harry] my name is harry`
- Speed up the "Kit" voice to 350 words per minute: `/say [:nk] [:rate 350] my name's Kit, and I can speak pretty quickly!`
- Use tones to play the beginning of the Tetris theme: `/say [:t430,500][:t320,250][:t350,250][:t390,500][:t350,250][:t330,250][:t290,500][:t290,250][:t350,250][:t430,500]`
- Dial the phone number "867-5309": `/say [:dial8675309]`
- The famous John Madden song: `/say [ey<900,24>iyuw<450,27>ey<900,34>iyuw<450,32>jhah<900,27>nmae<225,25>ae<225,24>deh<1350,22>n]`
- Pitch down the default voice: `/say [:dv ap 5] my name's Paul`
- Create a demonic child to do your evil bidding: `/say [:nk] started at the top [:dv ap 2 ri 90 hs 125] [:rate 150] now we're down here.`

## Links

You can check out the sources for Hawking's preset phrases [here](https://github.com/naschorr/hawking-phrases), to see how those are created.

There's also a wealth of Moonbase Alpha guides on Steam, like [this one](https://steamcommunity.com/sharedfiles/filedetails/?id=128648903) which has some useful examples.
