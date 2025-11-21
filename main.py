import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import time

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=";", intents=intents)
tree = bot.tree

# =====================================================================
# MULTISERVER: info de cada servidor
# =====================================================================

guild_players = {}
# guild_id: {
#   "vc": voice,
#   "title": str,
#   "url": str,
#   "duration": int,
#   "start_time": timestamp,
#   "message": discord.Message,
#   "update_task": asyncio.Task,
#   "loop": False
# }

# =====================================================================
# YT-DLP + FFMPEG
# =====================================================================

ytdl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True
}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)
ffmpeg_opts = {"options": "-vn"}

# =====================================================================
# Obtener info (URL + título + duración)
# =====================================================================

def get_song(query):
    try:
        data = ytdl.extract_info(query, download=False)
    except:
        data = ytdl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]

    return {
        "url": data["url"],
        "title": data.get("title", "Unknown Title"),
        "duration": data.get("duration", 0)
    }

# =====================================================================
# Barra de progreso
# =====================================================================

def progress_bar(elapsed, total, size=20):
    if total == 0:
        return "░" * size
    filled = int((elapsed / total) * size)
    return "▓" * filled + "░" * (size - filled)

# =====================================================================
# UI (Botones)
# =====================================================================

class MusicUI(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="⏸ Pausar", style=discord.ButtonStyle.blurple)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = guild_players.get(self.guild_id)
        if player and player["vc"].is_playing():
            player["vc"].pause()
            await interaction.response.send_message("⏸ Pausado", ephemeral=True)

    @discord.ui.button(label="▶️ Reanudar", style=discord.ButtonStyle.green)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = guild_players.get(self.guild_id)
        if player and player["vc"].is_paused():
            player["vc"].resume()
            await interaction.response.send_message("▶️ Reanudado", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = guild_players.get(self.guild_id)
        if player and player["vc"].is_playing():
            player["loop"] = False
            player["vc"].stop()
        await interaction.response.send_message("⏭ Saltado", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.gray)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = guild_players.get(self.guild_id)
        player["loop"] = not player["loop"]
        estado = "activado" if player["loop"] else "desactivado"
        await interaction.response.send_message(f"🔁 Loop {estado}", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = guild_players.get(self.guild_id)
        if player:
            player["loop"] = False
            player["vc"].stop()
        await interaction.response.send_message("⏹ Detenido", ephemeral=True)

    @discord.ui.button(label="⏏️ Leave", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = guild_players.get(self.guild_id)
        if player:
            await player["vc"].disconnect()
            player["update_task"].cancel()
            del guild_players[self.guild_id]
        await interaction.response.send_message("👋 Desconectado", ephemeral=True)

# =====================================================================
# Actualización del mensaje cada 5s
# =====================================================================

async def update_nowplaying(guild_id):
    while True:
        player = guild_players.get(guild_id)
        if not player:
            return

        vc = player["vc"]
        if not vc.is_playing() and not player["loop"]:
            return

        elapsed = int(time.time() - player["start_time"])
        duration = player["duration"]

        # Si terminó la canción y hay loop
        if elapsed >= duration:
            if player["loop"]:
                # reiniciar canción
                await play_song(player["interaction"], player["url"])
                return
            else:
                return

        bar = progress_bar(elapsed, duration)
        msg = f"""
🎶 **{player['title']}**
`[{bar}]`
⏳ **{elapsed // 60}:{elapsed % 60:02d} / {duration // 60}:{duration % 60:02d}**
"""

        try:
            await player["message"].edit(content=msg, view=MusicUI(guild_id))
        except:
            pass

        await asyncio.sleep(5)

# =====================================================================
# Reproducir
# =====================================================================

async def play_song(interaction, query):
    guild_id = interaction.guild.id

    # unir al canal del usuario
    user = interaction.user
    if not user.voice:
        await interaction.followup.send("❌ Debes estar en un canal de voz.")
        return

    vc = interaction.guild.voice_client
    if vc is None:
        vc = await user.voice.channel.connect()
    else:
        if vc.channel != user.voice.channel:
            await vc.move_to(user.voice.channel)

    # obtener música
    data = get_song(query)
    source = await discord.FFmpegOpusAudio.from_probe(data["url"], **ffmpeg_opts)

    # si ya había una reproducción, cancelar la tarea vieja
    if guild_id in guild_players:
        old = guild_players[guild_id]
        if old["update_task"]:
            old["update_task"].cancel()

    vc.stop()
    vc.play(source)

    msg = await interaction.followup.send("🎶 Cargando canción...")

    guild_players[guild_id] = {
        "vc": vc,
        "title": data["title"],
        "url": query,
        "duration": data["duration"],
        "start_time": time.time(),
        "message": msg,
        "update_task": asyncio.create_task(update_nowplaying(guild_id)),
        "interaction": interaction,
        "loop": False
    }

# =====================================================================
# SLASH COMMANDS
# =====================================================================

@tree.command(name="play", description="Reproduce música en tu canal.")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    await play_song(interaction, query)

@tree.command(name="nowplaying", description="Muestra la canción actual.")
async def nowplaying(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    player = guild_players.get(guild_id)

    if not player:
        await interaction.response.send_message("📭 No hay canción sonando.")
        return

    await interaction.response.send_message(
        f"🎶 **{player['title']}**",
        view=MusicUI(guild_id)
    )

# =====================================================================
# READY
# =====================================================================

@bot.event
async def on_ready():
    print(f"✅ BOT ONLINE como {bot.user}")
    try:
        await tree.sync()
        print("✔ Slash commands listos.")
    except Exception as e:
        print("❌ Error sync:", e)

# =====================================================================
# RUN
# =====================================================================

bot.run(os.getenv("TOKEN"))
