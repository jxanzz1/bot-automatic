import discord
from discord.ext import commands
import wavelink
import asyncio
import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("1441472637217017946"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=";", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot iniciado como {bot.user}")

    # Conectar Lavalink
    await wavelink.NodePool.create_node(
        bot=bot,
        host="lavalink-realtime.up.railway.app",
        port=443,
        password="youshallnotpass",
        https=True
    )
    print("Lavalink conectado.")

    await connect_to_voice()


async def connect_to_voice():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    if channel and isinstance(channel, discord.VoiceChannel):
        if not channel.guild.voice_client:
            await channel.connect(cls=wavelink.Player)
            print("Conectado al canal 24/7.")
    else:
        print("❌ ERROR: ID del canal inválido.")


@bot.command()
async def play(ctx, *, search: str):
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect(cls=wavelink.Player)

    player: wavelink.Player = ctx.voice_client
    track = await wavelink.YouTubeTrack.search(query=search, return_first=True)
    await player.play(track)
    await ctx.send(f"🎧 Reproduciendo: **{track.title}**")


@bot.command()
async def pause(ctx):
    await ctx.voice_client.pause()
    await ctx.send("⏸ Pausado.")


@bot.command()
async def resume(ctx):
    await ctx.voice_client.resume()
    await ctx.send("▶ Reanudado.")


@bot.command()
async def stop(ctx):
    await ctx.voice_client.stop()
    await ctx.send("⏹ Detenido.")


@bot.command()
async def skip(ctx):
    await ctx.voice_client.stop()
    await ctx.send("⏭ Saltado.")


@bot.command()
async def volume(ctx, vol: int):
    player: wavelink.Player = ctx.voice_client
    await player.set_volume(vol)
    await ctx.send(f"🔊 Volumen: **{vol}%**")


bot.run(TOKEN)
