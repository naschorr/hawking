# Installing and Running Hawking

## Installing Hawking

### Manually

- Make sure you've got [Python 3.15](https://www.python.org/downloads/) installed, and support for virtual environments (This assumes that you're on Python 3.15 with `venv` support)
- Double check that you're installing into a clean directory. If there's an old version of Hawking or an old venv then this likely won't work!
- `cd` into the directory that you'd like the project to go (If you're on Linux, I'd recommend '/usr/local/bin')
- Clone the repository to your machine: `git clone https://github.com/naschorr/hawking`
- Create a Python virtual environment inside the cloned repository: `python3.15 -m venv hawking/`
  - You may need to run: `apt install python3.15-venv` to enable virtual environments for Python 3.15 on Linux
- `cd hawking/`
- Activate your newly created venv (Run `source bin/activate` on Linux, or `.\Scripts\activate` on Windows)
- Install dependencies with: `pip install -r requirements.txt` (If you run into any issues with this, try running `pip install -r minimal-requirements.txt`. This installs the bare minimum number of packages and thus forces dependencies to resolve their dependencies automatically.)
  - If you run into issues during `PyNaCl`'s installation on Linux, you may need to run: `apt install build-essential libffi-dev python3.15-dev` to install some supplemental features for the setup process.
  - If you run into issue during `cffi`'s installation on Windows, you may need to install the Microsoft C++ Build Tools. You can find them [here](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
- Make sure the [FFmpeg executable](https://www.ffmpeg.org/download.html) is in your system's `PATH` variable
- Create a [Discord app](https://discordapp.com/developers/applications/me), flag it as a bot, and make a note of the bot's token.
- Register the Bot with your server. Go to: `https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=53803072`, but make sure to replace CLIENT_ID with your bot's client id.
- Select your server, and hit "Authorize"
- Set up the bot's `configuration/.env` file
  - Rename the `configuration/.env.example` to `configuration/.env`
  - Set the file's `HAWKING__CORE__DISCORD__TOKEN` value to the token from earlier
  - Feel free to update the other values if you'd like to use those features as well
- (Optionally) Update values in the bot's `configuration/config.json` file. See the [configuration guide](https://github.com/naschorr/hawking/blob/master/docs/configuring_hawking.md) for more info on configuring Hawking.

> *Note:* Linux-based installations will require some extra tweaks to run Hawking, so check out the rest of this guide.

### Windows Installation

Nothing else to do! Everything should work just fine.

### Linux Installation

Running Hawking on Linux requires a bit more work. At a minimum check out the Minimum Installation section, which covers getting Wine installed. If you're planning on running this in a headless server environment, also check out the Headless Installation section as well.

#### Minimum Installation

At an absolute minimum, you'll need to install [Wine](https://www.winehq.org/) to get the text-to-speech executable working. On Ubuntu you can do the following:

- `dpkg --add-architecture i386`
- `apt-get update`
- `apt-get install wine`

#### Headless Installation

Hawking (or rather the ancient text to speech software) needs a screen so that it can run, but that doesn't really make sense in a server context. To get around that we'll use Xvfb:

- Install Xvfb with your preferred package manager (`apt install xvfb` on Ubuntu, for example)
- Invoke Xvfb automatically on reboot with a cron job (`sudo crontab -e`), by adding `@reboot Xvfb :0 -screen 0 1024x768x16 &` to your list of jobs.
- Set `headless` to be `true` in the appropriate file in `configuration/`.
- If you're using different virtual server or screen identifiers, then make sure they work with `xvfb_prepend` in the appropriate file in `configuration/`. Otherwise everything should work fine out of the box.

### Docker

Want to get started without any fuss? You can use the Docker image to automate all of that.

- Clone the repository to your machine: `git clone https://github.com/naschorr/hawking`
  - If you're on Linux, try cloning into `git clone https://github.com/naschorr/hawking /opt/hawking`. This'll let you use the Docker helper scripts natively.
- Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- Create a [Discord app](https://discordapp.com/developers/applications/me), flag it as a bot, and make a note of the bot's token.
- Register the Bot with your server. Go to: `https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=53803072`, but make sure to replace CLIENT_ID with your bot's client id.
- Select your server, and hit "Authorize"
- Set up the bot's `configuration/.env` file
  - Rename the `configuration/.env.example` to `configuration/.env`
  - Set the file's `HAWKING__CORE__DISCORD__TOKEN` value to the token from earlier
  - Feel free to update the other values if you'd like to use those features as well
- (Optionally) Update values in the bot's `configuration/config.json` file. See the [configuration guide](https://github.com/naschorr/hawking/blob/master/docs/configuring_hawking.md) for more info on configuring Hawking.

## Running Hawking

### Manually

Want to play with Hawking's code, and don't really care about setting up services or containers? You're in the right place!

- `cd` into the project's root
- Activate the virtual environment (Run `source bin/activate` on Linux, or `.\Scripts\activate` on Windows)
- Run `python code/hawking/hawking.py` to start Hawking

### Linux-based Headless Installation

Want to get Hawking running natively on a Linux machine? This is the place!

> *Note:* This assumes that your system uses systemd. You can check that by running `pidof systemd && echo "systemd" || echo "other"` in the terminal. If your system is using sysvinit, then you can just as easily build a cron job to handle running the entrypoint on reboot. Just make sure to use your virtual environment's Python executable, and not the system's one.

- Assuming that your installation is in '/usr/local/bin/hawking', you'll want to move the `hawking.service` file into the systemd services folder with `mv hawking.service /etc/systemd/system/`
  - If your Hawking installation is located elsewhere, update the paths (`ExecStart` and `WorkingDirectory`) inside `hawking.service` to point to your installation.
- Get the service working with `sudo systemctl daemon-reload && systemctl enable hawking && systemctl start hawking --no-block`
- Now you can control the Hawking service just like any other. For example, to restart: `sudo service hawking restart`

### Docker

#### Running a Prebuilt Image

Just like any other Docker container, you can spin it up with something like:
```bash
docker run --detach \
  --pull always \
  --name hawking \
  --init \
  --env-file /opt/hawking/configuration/.env \
  --mount type=bind,source=/opt/hawking/configuration/,target=/app/configuration,readonly \
  --mount type=volume,source=hawking-logs,target=/app/logs \
  --mount type=volume,source=hawking-privacy,target=/app/privacy \
  ghcr.io/naschorr/hawking:latest
```

Alternatively if you're on Linux, you can use the handy helper scripts inside `docker/scripts` to handle starting and stopping the container. To start it up (and keep it running) use: `docker/scripts/start.sh`. Likewise use: `docker/scripts/stop.sh` to stop it for good.

#### Running a Custom Image

From the repository root, run `docker compose -f docker/compose.yaml up --build` to start it up! This is handy if you've made changes to the code and want to run a fresh container with those changes included.
