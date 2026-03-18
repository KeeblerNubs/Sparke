# Discord Invite Role Bot

This repository contains a simple Discord bot that grants a role to new
members based on the invite they used to join the server. The project ships
with a Docker-based workflow so it can run without requiring Python to be
installed on the host. On Windows, you can build and run everything with a
single PowerShell command.

## Prerequisites

* Docker Desktop or another Docker runtime
* A Discord bot token with the **Server Members Intent** and **Message Content
  Intent** enabled

## Running the bot via Docker

1. Clone this repository and open a PowerShell terminal in the project root.
2. Set your bot token in the current session:

   ```powershell
   $env:DISCORD_TOKEN = "<your token>"
   ```

   Alternatively, pass the token to the script with the `-Token` parameter.
3. Build and start the bot:

   ```powershell
   ./run.ps1
   ```

   The script builds the Docker image (if necessary) and starts a container
   with the token injected as an environment variable. Logs from the bot are
   streamed to your terminal.

To build the image without starting the container, run:

```powershell
./run.ps1 -BuildOnly
```

## Commands

While the bot is running, the following prefix commands are available inside a
Discord guild (server) where the bot is present:

* `!dashboard` / `/dashboard` – Open an interactive dashboard with popup
  menus for **Admin Control** and **User Control**.
* `!createinvite @Role [max_uses] [max_age]` – Create a unique invite for the
  current channel and associate it with a role.
* `!listinvites` – List the currently tracked invite-to-role mappings.
* `!clearinvites` – Remove all invite-to-role mappings.

Roles are assigned automatically when new members join using a tracked invite.

## Development without Docker

If you prefer to run the bot locally, create a Python virtual environment and
install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use .venv\\Scripts\\Activate.ps1
pip install --editable .
```

Set `DISCORD_TOKEN` in your shell and start the console entry point that the
package exposes:

```bash
export DISCORD_TOKEN="<your token>"
invite-role-bot
```

The legacy workflow of installing from `requirements.txt` and running
`python bot.py` still works if you prefer not to install the package.

## Building distributable artifacts

To produce a wheel and source distribution, install the `build` tool and run

```bash
python -m pip install --upgrade build
python -m build
```

The resulting artifacts are placed in the `dist/` directory. They can be copied
to another machine and installed with `pip install <artifact>` to reproduce a
ready-to-run bot without cloning the repository.
