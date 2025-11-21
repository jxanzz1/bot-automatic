import os
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import time

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=";", intents=intents)
tree = bot.tree

# === CONFIGURACIÓN YT-DLP ===
ytdl_format_options = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
ffmpeg_options = {"options": "-vn"}

# === SISTEMA MULTISERVIDOR ===
guild_states = {}  # Cada server tendrá su propia cola y estado


# --- FUNCIONES ---
def get_state(guild_id):
    if guild_id not in guild_states:
        guild_states[guild_id] = {
            "queue": [],
            "now": None,
            "loop": False,
            "start": 0,
            "duration": 0
        }
    return guild_states[guild_id]


async def join(interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        return vc

    if interaction.user.voice is None:
        await interaction.response.send_message("❌ Debes estar en un canal de voz.")
        return None

    channel = interaction.user.voice.channel
    return await channel.connect()


def make_progress_bar(current, total, length=22):
    progress = int((current / total) * length)
    bar = "▓" * progress + "░" * (length - progress)
    return bar


async def update_message(interaction, state, message):
    while True:
        vc = interaction.guild.voice_client
        if vc is None or not vc.is_playing():
            break

        elapsed = int(time.time() - state["start"])
        bar = make_progress_bar(elapsed, state["duration"])
        cur = time.strftime("%M:%S", time.gmtime(elapsed))
        total = time.strftime("%M:%S", time.gmtime(state["duration"]))

        embed_text = (
            f"🎶 **{state['now']['title']}**\n\n"
            f"`[{bar}]`\n\n"
            f"⏳ **{cur} / {total}**"
        )

        try:
            await message.edit(content=embed_text)
        except:
            pass

        await asyncio.sleep(2)


async def play_next(interaction):
    state = get_state(interaction.guild.id)
    if state["loop"] and state["now"]:
        await play_song(interaction, state["now"]["url"])
        return

    if len(state["queue"]) > 0:
        song = state["queue"].pop(0)
        await play_song(interaction, song["url"])
    else:
        state["now"] = None


async def play_song(interaction, query):
    state = get_state(interaction.guild.id)
    vc = await join(interaction)
    await interaction.response.defer()

    try:
        info = ytdl.extract_info(query, download=False)
    except:
        info = ytdl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]

    url = info["url"]
    title = info.get("title", "Unknown")
    duration = int(info.get("duration", 0))

    state["now"] = {"title": title, "url": query}
    state["duration"] = duration
    state["start"] = time.time()

    source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

    def after_play(err):
        fut = asyncio.run_coroutine_threadsafe(play_next(interaction), bot.loop)
        try:
            fut.result()
        except:
            pass

    vc.play(source, after=after_play)

    bar = make_progress_bar(0, duration)
    msg = await interaction.followup.send(
        f"🎶 **{title}**\n\n"
        f"`[{bar}]`\n\n"
        f"⏳ **00:00 / {time.strftime('%M:%S', time.gmtime(duration))}**"
    )

    bot.loop.create_task(update_message(interaction, state, msg))


# === SLASH COMMANDS ===
@tree.command(name="play", description="Reproduce una canción o URL")
async def play(interaction: discord.Interaction, query: str):
    state = get_state(interaction.guild.id)
    vc = interaction.guild.voice_client

    if vc and vc.is_playing():
        state["queue"].append({"url": query})
        await interaction.response.send_message(f"➕ Añadido a la cola.")
    else:
        await play_song(interaction, query)


@tree.command(name="skip", description="Salta la canción actual")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
    await interaction.response.send_message("⏭ Saltado.")


@tree.command(name="stop", description="Detiene todo")
async def stop(interaction: discord.Interaction):
    state = get_state(interaction.guild.id)
    vc = interaction.guild.voice_client

    state["queue"] = []
    state["now"] = None

    if vc:
        vc.stop()

    await interaction.response.send_message("⏹ Detenido.")


@tree.command(name="leave", description="Saca al bot del canal de voz")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
    await interaction.response.send_message("❌ Desconectado.")


@tree.command(name="queue", description="Muestra la cola")
async def queue(interaction: discord.Interaction):
    state = get_state(interaction.guild.id)
    if not state["queue"]:
        await interaction.response.send_message("📭 Cola vacía.")
        return

    lines = [f"{i+1}. {s['url']}" for i, s in enumerate(state["queue"])]
    await interaction.response.send_message("📜 Cola:\n" + "\n".join(lines))


# === READY EVENT ===
@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    try:
        await tree.sync()
        print("Slash commands listos")
    except Exception as e:
        print(f"Error sync: {e}")


bot.run(os.getenv("TOKEN"))
