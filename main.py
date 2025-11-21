import os
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=";", intents=intents)
tree = bot.tree

VOICE_CHANNEL_ID = 1441472637217017946  # 👈 Reemplaza por el ID del canal de voz

# --- CONFIGURACIÓN DE YT-DLP ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
}
ffmpeg_options = {'options': '-vn'}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
queue = []
now_playing = None
loop_mode = False


# --- FUNCIONES ---
async def join_vc(guild):
    vc = guild.voice_client
    if vc is None:
        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if channel:
            vc = await channel.connect()
    return vc


async def play_next(interaction):
    global now_playing
    if loop_mode and now_playing:
        await play_song(interaction, now_playing['url'])
        return

    if queue:
        song = queue.pop(0)
        await play_song(interaction, song['url'])
    else:
        now_playing = None


async def play_song(interaction, query):
    global now_playing
    vc = await join_vc(interaction.guild)

    try:
        data = ytdl.extract_info(query, download=False)
    except Exception:
        data = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]

    url = data['url']
    title = data.get('title', 'Unknown')
    now_playing = {'title': title, 'url': query}

    source = await discord.FFmpegOpusAudio.from_probe(url, **ffmpeg_options)
    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction), bot.loop))

    await interaction.followup.send(
        f"🎶 **Reproduciendo:** `{title}`",
        view=MusicButtons()
    )


# --- BOTONES PREMIUM ---
class MusicButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏸ Pausar", style=discord.ButtonStyle.blurple)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Música pausada", ephemeral=True)

    @discord.ui.button(label="▶️ Reanudar", style=discord.ButtonStyle.green)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Música reanudada", ephemeral=True)

    @discord.ui.button(label="⏭ Saltar", style=discord.ButtonStyle.gray)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭ Canción saltada", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.gray)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        global loop_mode
        loop_mode = not loop_mode
        estado = "activado" if loop_mode else "desactivado"
        await interaction.response.send_message(f"🔁 Loop {estado}", ephemeral=True)

    @discord.ui.button(label="⏹ Detener", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        global queue
        vc = interaction.guild.voice_client
        queue = []
        if vc:
            vc.stop()
        await interaction.response.send_message("⏹ Reproducción detenida", ephemeral=True)


# --- COMANDOS SLASH ---
@tree.command(name="play", description="Reproduce una canción o URL")
async def play(interaction: discord.Interaction, *, query: str):
    await interaction.response.defer()
    global now_playing

    vc = await join_vc(interaction.guild)

    if vc.is_playing() or vc.is_paused():
        queue.append({'url': query})
        await interaction.followup.send(f"➕ Añadido a la cola: `{query}`")
    else:
        await play_song(interaction, query)


@tree.command(name="skip", description="Salta la canción actual")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭ Canción saltada")


@tree.command(name="stop", description="Detiene la música y limpia la cola")
async def stop(interaction: discord.Interaction):
    global queue
    vc = interaction.guild.voice_client
    queue.clear()
    if vc:
        vc.stop()
    await interaction.response.send_message("🛑 Música detenida y cola limpiada")


@tree.command(name="queue", description="Muestra la cola actual")
async def queue_cmd(interaction: discord.Interaction):
    if not queue:
        await interaction.response.send_message("📭 La cola está vacía")
    else:
        lista = "\n".join([f"{i+1}. {s['url']}" for i, s in enumerate(queue)])
        await interaction.response.send_message(f"📜 **Cola:**\n{lista}")


@tree.command(name="leave", description="Desconecta al bot del canal de voz")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("❌ Desconectado del canal")


# --- EVENTO ON_READY ---
@bot.event
async def on_ready():
    print(f"✅ Conectado como {bot.user}")
    try:
        await tree.sync()
        print("✅ Slash commands sincronizados correctamente.")
    except Exception as e:
        print(f"Error al sincronizar: {e}")


bot.run(os.getenv("TOKEN"))
