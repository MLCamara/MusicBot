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
import requests

from queue import Queue

# Load environment variables from a .env file
load_dotenv()
discord_token = os.getenv('token')
icon = os.getenv('icon')

# Options for youtube_dl to fetch the best audio and avoid playlists
ydl_opts = {'format': 'bestaudio', 'noplaylist': 'True'}

playlist_opts = {'format': 'bestaudio'}

# FFmpeg options for reconnecting to streams and setting audio volume
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                  'options': '-vn -filter:a "volume=0.50"'}


guilds_tracklist = {} #dict of guilds (key) and tracklist (value) to keep note of the guild's queues

# Create bot with specified intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)


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
            guilds_tracklist[ctx.guild] = Queue()
        else:
            await ctx.send("**You need to be in a voice channel to use this command!**")
            return
    elif voice_client.channel != ctx.author.voice.channel and ctx.author.voice:
        await voice_client.disconnect()
        await ctx.author.voice.channel.connect()
        guilds_tracklist[ctx.guild] = Queue()

    # Extract the track name from the message content
    msg: str = ctx.message.content
    track_name = msg.replace('!play', '').strip().replace(' ', '+')

    data = await download(track_name, ctx)
    try:

        source = data['source']
    except Exception as e:
        print(e)
        print('Source not donwloaded successfully')
        return

    source = data['source']
    title = data['title']
    source = data['source']
    url = data['url']
    image = data['image']
    embed = embedded(url,title,image)
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client.is_playing():
        voice_client.stop()

    ctx.voice_client.play(source, after=lambda e:  after_playback(ctx=ctx))
    await ctx.send(f"***Now playing:***\n  ", embed=embed)

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


@bot.command(name='p')
async def resume(ctx: context):
    """
    Resumes the currently paused audio.

    Args:
        ctx (context): The command context, including message and author information.
    """

    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients,guild=ctx.guild)
    if voice_client:
        if ctx.author.voice and ctx.author.voice.channel == voice_client.channel:
            if voice_client.is_playing():
                voice_client.pause()
                print('Bot is paused.')
                await ctx.send("**Bot is paused.**")
            else:
                voice_client.resume()
                print('Bot is resumed.')
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
            guilds_tracklist.pop(ctx.guild)
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

    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        await ctx.send("**I am not connected to a voice channel.**")
        return

    if voice_client.channel != ctx.author.voice.channel:
        await ctx.send("**You must be in the same voice channel to use this command!")
        return

    data = await download(track_name, ctx=ctx)
    tracklist: Queue = guilds_tracklist.get(ctx.guild)

    source = data['source']
    title = data['title']
    url = data['url']
    image = data['image']

    tracklist.put(data)
    guilds_tracklist[ctx.guild] = tracklist
    embed = embedded(url, title, image)
    await ctx.send(f"***Added to queue:***\n  ", embed=embed)
    print(f"{data}\n Added to Queue, {ctx.guild}")


    if not voice_client.is_playing():
        ctx.voice_client.play(source,after=lambda e: after_playback(ctx=ctx))
        await ctx.send(f"\n***Now playing from queue:***\n  ", embed=embed)
        guilds_tracklist[ctx.guild] = Queue()



    #Function safely plays next track in a new thread
async def after_playback(ctx, err= None):
    asyncio.run_coroutine_threadsafe(my_after(ctx=ctx),bot.loop)

async def my_after(error, ctx):
    """
    Handles the completion of a song, plays the next one if available, and notifies users.

    Args:
        error (Exception): Playback error, if any.
        ctx (context): The command context to send messages and manage playback.
    """
    playlist = guilds_tracklist.get(ctx.guild)
    # Check if there are more tracks in the queue
    if not playlist.empty():
        # Get the next track from the queue
        data = playlist.get()
        title = data['title']
        source = data['source']
        url = data['url']
        image = data['image']

        # Get the voice client
        voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        if voice_client:
            voice_client.play(source, after=lambda e: after_playback(ctx=ctx))
            embed = embedded(url, title, image)
            # Notify the user about the next track
            await ctx.send(f"\n***Now playing from queue:***\n", embed = embed)
            guilds_tracklist[ctx.guild] = playlist
        else:
            await ctx.send("I am not connected to a voice channel.")
    else:
        # Notify that the queue is empty
        await ctx.send("**The queue is empty. Add more tracks to keep the party going!**")

@bot.command(name='list')
async def list(ctx: context):
    voice_client: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        playlist = guilds_tracklist.get(ctx.guild)
        if not playlist.empty():
            i = 1
            for _ in range(playlist.qsize()):
                data = playlist.get()
                await ctx.send(f"***{i}. {data['title']}***")  # Process the dictionary
                i += 1
                playlist.put(data)
        else:
            await ctx.send('**No tracks in Queue**')
    else:
        await ctx.send('**I am not connected to a voice channel.**')

@bot.command(name='skip')
async def skip(ctx: context):
    voice: discord.VoiceClient = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice: #is the bot connected to a voice channel
        if ctx.author.voice and ctx.author.voice.channel == voice.channel: #is bot and author in the same voice channel
            if voice.is_playing(): #is it playing

                voice.stop() #stops the currently playing track
                await ctx.send("***Skipped!***")
                print(f'song skipped, {ctx.guild}')
                playlist = guilds_tracklist.get(ctx.guild)
                if not playlist.empty(): #is the queue not empty

                    data = playlist.get()
                    source = data['source']
                    title = data['title']
                    url = data['url']
                    image = data['image']
                    ctx.voice_client.play(source,after=lambda e: after_playback(ctx=ctx))
                    embed = embedded(url,title,image)
                    await ctx.send(f"\n***Now playing from queue:***\n",embed = embed)
                    guilds_tracklist[ctx.guild] = playlist

            elif not playlist.empty(): #queue is empty
                await ctx.send("**The queue is empty. Add more tracks to keep the party going!**")
        else: #author is not in the same voice channel or is not in a voice channel at all
            await ctx.send("**You need to be in the same voice channel to use this command!**")
    else:#bot is not connected to a voice channel
        await ctx.send("**I am not connected to a voice channel.**")

def embedded(url: str, vid_title: str, thumbnail: str):
    embed = discord.Embed(title=vid_title, description="Click to watch", color=discord.Color.dark_red(), url = url)
    embed.set_thumbnail(url=thumbnail)
    embed.add_field(name="Video", value=url, inline=False)
    return embed

async def download(trackname: str, ctx: context):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            # Fetch track information asynchronously
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(f"ytsearch:{trackname}", download=False)['entries'][0]
            )

            title = info['title']  # Title of the track
            song = info['url']  # url of audio
            url = info['original_url']
            image = info['thumbnail']
            source = FFmpegOpusAudio(song, **FFMPEG_OPTIONS)
            data = {'title': title, 'source': source, 'url': url, 'image': image}
            return data
        except Exception as e:
            # Handle errors (e.g., track not found)
            print(e)
            await ctx.send("**Could not Find Track.**")

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(
        title="**COMMANDS**",
        description="Here are the commands you can use:",
        color=discord.Color.dark_red()
    )
    embed.add_field(name="**!help**", value="list all commands", inline=False)
    embed.add_field(name="**!play**", value="plays track", inline=False)
    embed.add_field(name="**!next**", value="queues track.", inline=False)
    embed.add_field(name="**!p**", value="Play/Pause", inline=False)
    embed.add_field(name="**!skip**", value="skips the current track ", inline=False)
    embed.add_field(name="**!list**", value="Shows all tracks in the queue", inline=False)
    embed.add_field(name="**!goon**", value="bot goons to death and disconnects from vc ", inline=False)
    embed.set_footer(text="Enjoy your music! 🎵\n **Created by Mohamed Camara\n IG: @stackedmc_**", icon_url=icon)

    await ctx.send(embed=embed)

# Run the bot with the token from the .env file
bot.run(discord_token)