import os
import discord
from discord.ext import commands
from discord import app_commands
import youtube_dl
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=";", intents=intents)
tree = bot.tree

VOICE_CHANNEL_ID = 1441472637217017946  # <-- PON AQUÍ EL ID DEL CANAL DE VOZ

# -----------------------------
# CONFIGURACIÓN DE YOUTUBE_DL
# -----------------------------
ytdl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True
}
ytdl = youtube_dl.YoutubeDL(ytdl_opts)

ffmpeg_options = {
    'options': '-vn'
}

# -----------------------------
# COLA DE MÚSICA
# -----------------------------
queue = []
now_playing = None
loop_mode = False
volume_level = 0.5  # 50%


# -----------------------------
# REPRODUCIR UNA CANCIÓN
# -----------------------------
async def play_next(ctx):
    global now_playing, queue, loop_mode

    if loop_mode and now_playing:
        await play_song(ctx, now_playing["url"])
        return

    if len(queue) == 0:
        now_playing = None
        return

    next_song = queue.pop(0)
    await play_song(ctx, next_song["url"])


async def play_song(ctx, query):
    global now_playing

    vc = ctx.voice_client
    if vc is None:
        vc = await ctx.user.voice.channel.connect()

    data = ytdl.extract_info(query, download=False)
    url = data['url']
    title = data.get('title', 'Unknown')

    now_playing = {"title": title, "url": query}

    source = await discord.FFmpegOpusAudio.from_probe(url, **ffmpeg_options)
    source.volume = volume_level

    vc.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(ctx),
            bot.loop
        )
    )

    await ctx.edit_original_response(
        content=f"🎶 **Reproduciendo:** `{title}`",
        view=MusicButtons()
    )


# -----------------------------
# BOTONES ESTILO JAR.RIP
# -----------------------------
class MusicButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏸/▶️", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Pausado", ephemeral=True)
        else:
            vc.resume()
            await interaction.response.send_message("▶️ Reanudado", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.green)
    async def skip(self, interaction, button):
        vc = interaction.guild.voice_client
        vc.stop()
        await interaction.response.send_message("⏭ Saltado", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction, button):
        global queue
        vc = interaction.guild.voice_client
        queue = []
        vc.stop()
        await interaction.response.send_message("⏹ Música detenida", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.gray)
    async def loop(self, interaction, button):
        global loop_mode
        loop_mode = not loop_mode
        estado = "activado" if loop_mode else "desactivado"
        await interaction.response.send_message(f"🔁 Loop {estado}", ephemeral=True)

    @discord.ui.button(label="🔉 Vol -", style=discord.ButtonStyle.gray)
    async def vol_down(self, interaction, button):
        global volume_level
        volume_level = max(0, volume_level - 0.1)
        await interaction.response.send_message(f"🔉 Volumen: {int(volume_level*100)}%", ephemeral=True)

    @discord.ui.button(label="🔊 Vol +", style=discord.ButtonStyle.gray)
    async def vol_up(self, interaction, button):
        global volume_level
        volume_level = min(1, volume_level + 0.1)
        await interaction.response.send_message(f"🔊 Volumen: {int(volume_level*100)}%", ephemeral=True)


# -----------------------------
# SLASH COMMANDS
# ----------------------------- 
@tree.command(name="play", description="Reproduce una canción")
async def play_cmd(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    global queue

    if interaction.guild.voice_client is None:
        channel = interaction.guild.get_channel(VOICE_CHANNEL_ID)
        await channel.connect()

    queue.append({"url": query})
    if len(queue) == 1 and now_playing is None:
        await play_song(interaction, query)
    else:
        await interaction.followup.send(f"➕ Añadido a la cola: `{query}`")


@tree.command(name="queue", description="Muestra la cola")
async def queue_cmd(interaction: discord.Interaction):
    if len(queue) == 0:
        await interaction.response.send_message("📭 La cola está vacía")
        return

    msg = "\n".join([f"{i+1}. {s['url']}" for i, s in enumerate(queue)])
    await interaction.response.send_message(f"📜 **Cola:**\n{msg}")


@tree.command(name="leave", description="Desconecta al bot")
async def leave_cmd(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()

    await interaction.response.send_message("❌ Bot desconectado")


# -----------------------------
# STARTUP
# -----------------------------
@bot.event
async def on_ready():
    print(f"Bot listo como {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

bot.run(os.getenv("TOKEN"))
