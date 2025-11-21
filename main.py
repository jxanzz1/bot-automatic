import discord
from discord.ext import commands
import asyncio
import yt_dlp
import datetime
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# Configuración de yt-dlp + ffmpeg
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True
}

FFMPEG_OPTIONS = {
    "options": "-vn"
}

# Reproductor global (sin cola por servidor)
current_song = {}
vc_dict = {}  # Guarda voice_client por guild

# ============
# BOTONES
# ============

class MusicControls(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="⏯️ Play/Pause", style=discord.ButtonStyle.secondary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = vc_dict.get(self.guild_id)
        if vc:
            if vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸️ Pausado", ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶️ Reanudado", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = vc_dict.get(self.guild_id)
        if vc:
            vc.stop()
            await interaction.response.send_message("⏭️ Canción saltada", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.secondary)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = vc_dict.get(self.guild_id)
        if vc:
            vc.stop()
            await vc.disconnect()
            current_song.pop(self.guild_id, None)
            vc_dict.pop(self.guild_id, None)
            await interaction.response.send_message("⏹️ Música detenida", ephemeral=True)

# ============
# FUNCIONES
# ============

async def start_playing(ctx, url):
    guild_id = ctx.guild.id

    if not ctx.author.voice:
        return await ctx.send("❌ Debes estar en un canal de voz.")
    channel = ctx.author.voice.channel

    if guild_id not in vc_dict or not vc_dict[guild_id].is_connected():
        vc = await channel.connect()
        vc_dict[guild_id] = vc
    else:
        vc = vc_dict[guild_id]

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info["url"]
            title = info.get("title", "Desconocido")
            duration = info.get("duration", 0)
            current_song[guild_id] = {"title": title, "duration": duration, "url": url, "start": asyncio.get_event_loop().time()}

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(finish_song(guild_id), bot.loop))
    except Exception as e:
        print("Error:", e)
        await ctx.send("❌ Ocurrió un error al reproducir la canción.")
        return

    # Embed con barra de progreso animada
    embed = discord.Embed(title=f"🎶 Reproduciendo ahora:", description=f"**{title}**", color=discord.Color.white())
    embed.add_field(name="Duración", value=progress_bar_animated(0, duration, 20))
    message = await ctx.send(embed=embed, view=MusicControls(guild_id))

    # Actualizar barra de progreso cada segundo
    async def update_progress():
        while vc.is_playing() or vc.is_paused():
            elapsed = int(asyncio.get_event_loop().time() - current_song[guild_id]["start"])
            bar = progress_bar_animated(elapsed, duration, 20)
            embed.set_field_at(0, name="Duración", value=f"{format_time(elapsed)} / {format_time(duration)} {bar}")
            try:
                await message.edit(embed=embed)
            except:
                pass
            await asyncio.sleep(1)
    bot.loop.create_task(update_progress())

async def finish_song(guild_id):
    current_song.pop(guild_id, None)
    vc_dict.pop(guild_id, None)

# ============
# COMANDOS
# ============

@bot.command()
async def play(ctx, url):
    await start_playing(ctx, url)

@bot.command()
async def stop(ctx):
    vc = vc_dict.get(ctx.guild.id)
    if vc:
        vc.stop()
        await vc.disconnect()
        current_song.pop(ctx.guild.id, None)
        vc_dict.pop(ctx.guild.id, None)
        await ctx.send("⏹️ Música detenida y bot desconectado.")

@bot.command()
async def pause(ctx):
    vc = vc_dict.get(ctx.guild.id)
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Pausado")

@bot.command()
async def resume(ctx):
    vc = vc_dict.get(ctx.guild.id)
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Reanudado")

# ============
# FUNCIONES AUXILIARES
# ============

def format_time(seconds):
    return str(datetime.timedelta(seconds=seconds))

def progress_bar_animated(current, total, length=20):
    """Barra de progreso animada tipo visualizador Jar"""
    if total == 0:
        return "[{}]".format("—"*length)
    filled = int(length * current // total)
    pointer = "🔘" if filled < length else "█"
    bar = "█"*filled + pointer + "—"*(length - filled - 1 if filled < length else 0)
    return f"[{bar}]"

# ============
# ENCENDIDO
# ============

@bot.event
async def on_ready():
    print(f"Bot activo como {bot.user}")

# --- Correr el bot con token seguro ---
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ La variable de entorno DISCORD_BOT_TOKEN no está configurada.")
bot.run(TOKEN)
