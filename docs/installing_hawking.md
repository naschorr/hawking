# Installing Hawking

## Basic Installation
- Make sure you've got [Python 3.6](https://www.python.org/downloads/) installed, and support for virtual environments (This assumes that you're on Python 3.6 with `venv` support, but Discord.py requires at least 3.5.3 currently)
- Double check that you're installing int a clean directory. If there's an old version of Hawking or an old venv then this likely won't work!
- `cd` into the directory that you'd like the project to go (If you're on Linux, I'd recommend '/usr/local/bin')
- `git clone https://github.com/naschorr/hawking`
- `python3.6 -m venv hawking/`
    + You may need to run: `apt install python3.6-venv` to enable virtual environments for Python 3.6 on Linux
- Activate your newly created venv
- `pip install -r requirements.txt`
    + If you run into issues during PyNaCl's installation, you may need to run: `apt install build-essential libffi-dev python3.6-dev` to install some supplemental features for the setup process.
- Make sure the [FFmpeg executable](https://www.ffmpeg.org/download.html) is in your system's `PATH` variable
- Create a [Discord app](https://discordapp.com/developers/applications/me), flag it as a bot, and put the bot token inside `config.json`, next to the `discord_token` key.
- Register the Bot with your server. Go to: `https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=53803072`, but make sure to replace CLIENT_ID with your bot's client id.
- Select your server, and hit "Authorize"
- Check out `config.json` for any configuration you might want to do. It's set up to work well out of the box, but you may want to add admins, change pathing, or modify the number of votes required for a skip. Note that linux based installations will require some extra tweaks to run Hawking, so check out the rest of this guide.

## Windows Installation
- Nothing else to do! Everything should work just fine.

## Linux Installation
Running Hawking on Linux requires a bit more work. At a minimum check out the Minimum Installation section, which covers getting Wine installed. If you're planning on running this in a headless server environment, also check out the Headless Installation section as well.

### Minimum Installation
At an absolute minimum, you'll needInstall [Wine](https://www.winehq.org/) to get the text-to-speech executable working. On Ubuntu you can do the following:
- `dpkg --add-architecture i386`
- `apt-get update`
- `apt-get install wine`

### Headless Installation
- Get Hawking set up with Xvfb
    + Install Xvfb with with your preferred package manager (`apt install xvfb` on Ubuntu, for example)
    + Invoke Xvfb automatically on reboot with a cron job (`sudo crontab -e`), by adding `@reboot Xvfb :0 -screen 0 1024x768x16 &` to your list of jobs.
    + Set `headless` to be `true` in `config.json`
    + If you're using different virtual server or screen identifiers, then make sure they work with `xvfb_prepend` in `config.json`. Otherwise everything should work fine out of the box.

- Hawking as a Service (HaaS)
    > *Note:* This assumes that your system uses systemd. You can check that by running `pidof systemd && echo "systemd" || echo "other"` in the terminal. If your system is using sysvinit, then you can just as easily build a cron job to handle running `hawking.py` on reboot. Just make sure to use your virtual environment's Python executable, and not the system's one.

    - Assuming that your installation is in '/usr/local/bin/hawking', you'll want to move the `hawking.service` file into the systemd services folder with `mv hawking.service /etc/systemd/system/`
        + If your hawking installation is located elsewhere, just update the paths (`ExecStart` and `WorkingDirectory`) inside the `hawking.service` to point to your installation.
    - Get the service working with `sudo systemctl daemon-reload && systemctl enable hawking && systemctl start hawking --no-block`
    - Now you can control the Hawking service just like any other. For example, to restart: `sudo service hawking restart`

## Manually Running Hawking
Don't want to use services? You can manually invoke Python to start up Hawking as well.
- `cd` into the project's root
- Activate the venv (`source bin/activate` on Linux, `.\Scripts\activate` on Windows)
- `cd` into `hawking/code/`
- Run `python hawking.py` to start Hawking
 