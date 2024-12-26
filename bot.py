'''
Author - Mohamed Camara
'''
from functools import partial
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
                  'options': '-vn -filter:a "volume=0.50"'}

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
    elif voice_client.channel != ctx.author.voice.channel and ctx.author.voice:
        await voice_client.disconnect()
        await ctx.author.voice.channel.connect()

    # Extract the track name from the message content
    msg: str = ctx.message.content
    track_name = msg.replace('!play', '').strip().replace(' ', '+')

    await asyncio.sleep(0.125) #sleeps for 125 millisecond to allow time to connect

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
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                voice_client.stop()

            source = FFmpegOpusAudio(song, **FFMPEG_OPTIONS)

            await asyncio.sleep(0.125)  # sleeps for 125 millisecond to allow time to connect
            ctx.voice_client.play(source,
                                  after=lambda error: asyncio.run_coroutine_threadsafe(my_after(error=error, ctx=ctx),bot.loop).result())
            await ctx.send(f"***Now playing:\n {title}***")
        except Exception as e:
            # Handle errors (e.g., track not found)
            print(e)
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
            voice_client.pause()
            await ctx.send("***Bot is paused.***")
            print('\nBot paused\n')
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
            await voice_client.disconnect()
            await ctx.send("***Bot Gooned to Death.***")
            print('\nBot Gooned to Death\n')
        else:
            await ctx.send("**You need to be in the same voice channel to use this command!**")
    else:
        await ctx.send("**I am not connected to a voice channel.**")

@bot.command(name='next')
async def next(ctx: context):
    # Extract the track name from the message content
    msg: str = ctx.message.content
    track_name = msg.replace('!next', '').strip().replace(' ', '+')

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            # Fetch track information asynchronously
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(f"ytsearch:{track_name}", download=False)['entries'][0]
            )
            title = info['title']  # Title of the track
            song = info['url']
            await asyncio.sleep(0.125)
            source = FFmpegOpusAudio(song, **FFMPEG_OPTIONS)
            data = {'title': title, 'source': source}
            tracklist.put(data)
            await ctx.send(f"***Added to queue\n {title}***")
            print('\nSTART OF QUEUE:')
            for e in list(tracklist.queue):
                print(e)
            print('END OF QUEUE\n')
            voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            if voice_client and voice_client.channel == ctx.author.voice.channel:
                if not voice_client.is_playing():
                    ctx.voice_client.play(source,
                                          after=lambda error: asyncio.run_coroutine_threadsafe(
                                              my_after(error=error, ctx=ctx), bot.loop).result())
                    await ctx.send(f"***Now playing from queue:\n {title}***")
        except Exception as e:
            # Handle errors (e.g., track not found)
            await ctx.send("**Could not Find Track.**")



async def my_after(error, ctx):
    """
    Handles the completion of a song, plays the next one if available, and notifies users.

    Args:
        error (Exception): Playback error, if any.
        ctx (context): The command context to send messages and manage playback.
    """
    if error:
        print(f"Playback error: {error}")
        return  # Stop further processing if there's an error

    # Check if there are more tracks in the queue
    if not tracklist.empty():
        # Get the next track from the queue
        data = tracklist.get()
        title = data['title']
        source = data['source']

        # Get the voice client
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if voice_client and voice_client.is_connected():
            # Play the next track
            def after_playback(err):
                asyncio.run_coroutine_threadsafe(my_after(err, ctx), bot.loop)

            voice_client.play(source, after=partial(after_playback))

            # Notify the user about the next track
            await ctx.send(f"***Now playing from queue:\n {title}***")
        else:
            await ctx.send("**You need to be in a voice channel to use this command!**")
    else:
        # Notify that the queue is empty
        await ctx.send("**The queue is empty. Add more tracks to keep the party going!**")

@bot.command(name='list')
async def list(ctx: context):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        if not tracklist.empty():
            i = 1
            for _ in range(tracklist.qsize()):
                data = tracklist.get()
                await ctx.send(f"***{i}. {data['title']}***")  # Process the dictionary
                i += 1
                tracklist.put(data)  # Put the dictionary back in the queue
        await ctx.send('**No tracks in Queue**')
    else:
        await ctx.send('**I am not connected to a voice channel.**')

# Run the bot with the token from the .env file
bot.run(discord_token)