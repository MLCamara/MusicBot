'''
Author - Mohamed Camara
'''
import discord
from discord import FFmpegOpusAudio
from discord.ext import commands
from discord.ext.commands import context
import os
from dotenv import load_dotenv
import yt_dlp as youtube_dl
import asyncio
from queue import Queue

# Load environment variables from a .env file
load_dotenv()
discord_token = os.getenv('token')

# Options for youtube_dl to fetch the best audio and avoid playlists
ydl_opts = {'format': 'bestaudio', 'noplaylist': 'True'}

playlist_opts = {'format': 'bestaudio'}

# FFmpeg options for reconnecting to streams and setting audio volume
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn -filter:a "volume=0.70"'}

tracklist = Queue()

# Create bot with specified intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command(name="play")
async def play(ctx: context):
    """
    Plays a track from YouTube in the user's current voice channel.

    Args:
        ctx (context): The command context, including message and author information.
    """
    # Ensure the bot is in a voice channel
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("**You need to be in a voice channel to use this command!**")
            return

    # Extract the track name from the message content
    msg: str = ctx.message.content
    track_name = msg.replace('!play', '').strip().replace(' ', '+')

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            # Fetch track information asynchronously
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(f"ytsearch:{track_name}", download=False)['entries'][0]
            )
            song = info['url']  # URL for streaming
            title = info['title']  # Title of the track

            # Stop any currently playing audio and play the new track
            ctx.voice_client.stop()
            source = FFmpegOpusAudio(song, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source)
            await ctx.send(f"***Now playing:\n {title}***")
        except Exception as e:
            # Handle errors (e.g., track not found)
            await ctx.send("**Could not Find Track.**")


@bot.command(name='pause')
async def pause(ctx: context):
    """
    Pauses the currently playing audio.

    Args:
        ctx (context): The command context, including message and author information.
    """
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients,guild=ctx.guild)
    if voice_client:
        if ctx.author.voice and ctx.author.voice.channel == voice_client.channel:
            ctx.voice_client.pause()
            await ctx.send("***Bot is paused.***")
        else:
            await ctx.send("**You need to be in the same voice channel to use this command!**")
    else:
        await ctx.send("**I am not connected to a voice channel.**")


@bot.command(name='resume')
async def resume(ctx: context):
    """
    Resumes the currently paused audio.

    Args:
        ctx (context): The command context, including message and author information.
    """

    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients,guild=ctx.guild)
    if voice_client:
        if ctx.author.voice and ctx.author.voice.channel == voice_client.channel:
            voice_client.resume()
            await ctx.send("**Bot is resumed.**")
        else:
            await ctx.send("**You need to be in the same voice channel to use this command!**")
    else:
        await ctx.send("**I am not connected to a voice channel.**")


@bot.command(name='goon')
async def leave(ctx: context):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients,guild=ctx.guild)
    if voice_client:
        if ctx.author.voice and ctx.author.voice.channel == voice_client.channel:
            await ctx.voice_client.disconnect()
            await ctx.send("***Bot is disconnected.***")
        else:
            await ctx.send("**You need to be in the same voice channel to use this command!**")
    else:
        await ctx.send("**I am not connected to a voice channel.**")



# Run the bot with the token from the .env file
bot.run(discord_token)