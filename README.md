# Discord Music Bot

A lightweight Discord music bot written in Python. It searches YouTube with
`yt-dlp`, streams audio into Discord through FFmpeg, and maintains a separate
in-memory queue for each server.

## Features

- Search for songs by name and stream the first YouTube result
- Play, pause, resume, and skip audio
- Queue additional tracks and view the current queue
- Keep queues separate across Discord servers
- Display track titles, thumbnails, and video links in Discord embeds
- Automatically reconnect FFmpeg streams when possible

## Requirements

- Python 3.10 or newer
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your
  system `PATH`
- A Discord application with a bot token
- The **Message Content Intent** enabled for the bot

## Installation

1. Clone the repository and enter the project directory:

   ```bash
   git clone https://github.com/MLCamara/MusicBot.git
   cd MusicBot
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, activate it with:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install the Python dependencies:

   ```bash
   pip install discord.py PyNaCl python-dotenv yt-dlp
   ```

4. Confirm that FFmpeg is installed:

   ```bash
   ffmpeg -version
   ```

## Discord bot setup

1. Open the [Discord Developer Portal](https://discord.com/developers/applications)
   and create an application.
2. Open the **Bot** page and create a bot user.
3. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
4. Copy the bot token for the environment configuration below.
5. In **OAuth2 > URL Generator**, select the `bot` scope and grant these bot
   permissions:
   - View Channels
   - Send Messages
   - Embed Links
   - Connect
   - Speak
6. Open the generated URL and add the bot to your server.

## Configuration

Create a `.env` file in the project root:

```env
token=YOUR_DISCORD_BOT_TOKEN
icon=https://example.com/bot-icon.png
ig=https://instagram.com/your-profile
```

| Variable | Required | Description |
| --- | --- | --- |
| `token` | Yes | Discord bot token used to sign in |
| `icon` | No | Image URL shown beside the author in the help embed |
| `ig` | No | Link used by the author name in the help embed |

Never commit your `.env` file or share your bot token. If a token is exposed,
reset it immediately in the Discord Developer Portal.

## Running the bot

Start the bot from the project directory:

```bash
python bot.py
```

When the bot connects, it posts a **Music Player is Ready** message and its help
embed in each server's system channel, or in the first text channel where it can
send messages.

## Commands

The command prefix is `!`.

| Command | Description | Example |
| --- | --- | --- |
| `!play <song>` | Search for and immediately play a track. If a track is already playing, it is replaced. | `!play Blinding Lights` |
| `!next <song>` | Add a track to the server's queue. If nothing is playing, start it immediately. | `!next Midnight City` |
| `!p` | Toggle between pause and resume. | `!p` |
| `!skip` | Skip the current track and play the next queued track, if available. | `!skip` |
| `!list` | Show all tracks currently in the queue. | `!list` |
| `!stop` | Disconnect the bot from the voice channel and clear the server queue. | `!stop` |
| `!help` | Display the command list in Discord. | `!help` |

To use playback controls, join a voice channel first. Most controls also require
you to be in the same voice channel as the bot.

## How it works

The bot uses `yt-dlp` to search YouTube and obtain an audio stream URL without
downloading the media file. `discord.py` passes that stream to FFmpeg, which
provides Opus audio to the Discord voice connection. Each Discord server uses
its own `Queue`, and the next queued track starts when playback finishes.

Audio volume is currently set to 25% in `FFMPEG_OPTIONS` inside `bot.py`.

## Troubleshooting

- **The bot receives no commands:** Make sure Message Content Intent is enabled
  both in the Developer Portal and in the code.
- **The bot joins but plays no audio:** Check that FFmpeg is installed and on
  your `PATH`, and that the bot has Connect and Speak permissions.
- **A track cannot be found:** Try a more specific song title or update `yt-dlp`
  with `pip install --upgrade yt-dlp`.
- **Playback stops after a restart:** Queues are stored only in memory and are
  cleared whenever the process restarts.

## Project structure

```text
MusicBot/
├── bot.py      # Bot commands, queue handling, embeds, and audio streaming
└── README.md   # Project documentation
```

## Author

Created by Mohamed Camara.
