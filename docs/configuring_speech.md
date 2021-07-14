# Speech Configuration with Hawking

Speech is modified with the same inline commands seen in Moonbase Alpha. They generally follow the pattern of `[:<command><parameter>]`, where the open bracket colon starts a command, `<command>` selects a specific command, and  `<parameter>` configures it. Some commands can be chained together, inside of a single set of brackets. Most commands can also be shortened down to a single letter, too.

## Changing Hawking's voice
Select a preset voice with the `[:name<n>]` command, where `<n>` is one of:
- `betty`
- `dennis`
- `frank`
- `harry`
- `kit`
- `paul` (this is the default voice)
- `rita`
- `ursula`
- `wendy`

You can also shorten the command to just `[:n<n>]` where `<n>` is the first letter of the name you want to use. For example: `[:nf]`.

## Changing how fast Hawking speaks
The rate of speech can be changed with `[:rate<r>]`, where `<r>` is the words per minute to speak. The default is 200, and must be between 75 and 600. For example, `[:rate100]` will cause all future speech to be spoken at 100 words per minute, which is half of the default.

## Playing tones and dialing phones
Tones are pure noise, simply a sound over a duration. They're usually used to simulate of beeps and boops. They follow the form `[:tone<f>,<l>]`, where `<f>` is the frequency of the tone, and `<l>` is the length of the tone in milliseconds. For example, `[:tone100,2000]` will generate a 100 hertz tone for 2 seconds, and `[:tone750,150]` will generate a beep at 750 hertz over 150 milliseconds.

Similar to tones is the dial command, which can be used to emulate the touch tones used when dialing a phone number (see the `\pizza` command). It takes the form `[:dial<n>]`, where `<n>` is the number to dial, though it can take any arbitrary amount of digits. For example, `[:dial8675309]` would generate the dial tone for the phone number "867-5309".

## Advanced customization
Customize the sound of the voice with `[:dv <commands>]`. This requires additional subcommands to fine-tune your desired behavior. Below are the more common/noticeable ones:
- Pitch can be changed with `ap <p>` where `<p>` is the average pitch in hertz.
- Change the size of the speaker\'s head with `hs <s>` where `<s>` is the amount of change in percentage. For example, `50` would represent a halved head size. Defaults to `100`.
- Gender can be changed with `sx <g>` where `<g>` is `0` for female, or `1` for male.
- Breathiness can be changed with `br <b>` where `<b>` is the amount of breathiness added in decibels. Default to `0`.
- Smoothness can be changed with `sm <s>` where `<s>` adjusts how smooth the voice sounds as a percentage. Defaults to `30`.
- Richness can be changed with `ri <r>`, where `<r>` is the amount of change in percentage. Defaults to `70`.

Note that the `[:dv]` command can support multiple subcommands, each one separated by a space. Also note that you can't have the subcommand next to its parameter, they must have a space between them. Check out these examples to get a feel for it:
- Set the average pitch to 15 hertz: `[:dv ap 15]`
- Increase the head size by 50%, and set the average pitch to 10 hertz: `[:dv hs 150 ap 10]`
- Set the gender to female, the averate pitch to 200 hertz, and half the head size: `[:dv sx 0 ap 200 hs 50]`
- Set the average pitch to 20 hertz, make the voice as un-smooth as possible, and 90% richness: `[:dv ap 20 sm 0 ri 90]`

## Examples
- Use the "Harry" voice: `\say [:name harry] my name is harry`
- Speed up the "Kit" voice to 350 words per minute: `\say [:nk] [:rate 350] my name's Kit, and I can speak pretty quickly!`
- Pitch down the default voice: `\say [:dv ap 5] my name's Paul`
- Create a demonic child to do your evil bidding: `\say [:nk] started at the top [:dv ap 2 ri 90 hs 125] [:rate 150] now we're down here.`

## Links
You can check out the sources for Hawking's preset phrases [here](https://github.com/naschorr/hawking-phrases), to see how those are created.

There's also a wealth of Moonbase Alpha guides on Steam, like [this one](https://steamcommunity.com/sharedfiles/filedetails/?id=128648903) which has some useful examples.
