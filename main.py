import os
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=";", intents=intents)
tree = bot.tree

# --- CONFIGURACIÓN DE YT-DLP ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
}
ffmpeg_options = {'options': '-vn'}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# Multi-servidor
queue = {}
now_playing = {}
loop_mode = {}


# --- FUNCIONES ---
async def join_vc(interaction):
    guild = interaction.guild
    vc = guild.voice_client

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ Debes estar en un **canal de voz**.", ephemeral=True)
        return None

    channel = interaction.user.voice.channel

    if vc and vc.channel != channel:
        await vc.move_to(channel)
    elif vc is None:
        vc = await channel.connect()

    return vc


async def play_next(guild_id, interaction):
    if loop_mode.get(guild_id) and now_playing.get(guild_id):
        await play_song(interaction, now_playing[guild_id]['url'])
        return

    if queue[guild_id]:
        song = queue[guild_id].pop(0)
        await play_song(interaction, song['url'])
    else:
        now_playing[guild_id] = None


async def play_song(interaction, query):
    guild = interaction.guild
    guild_id = guild.id

    vc = await join_vc(interaction)
    if vc is None:
        return

    try:
        data = ytdl.extract_info(query, download=False)
    except Exception:
        data = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]

    url = data['url']
    title = data.get('title', 'Unknown')

    now_playing[guild_id] = {'title': title, 'url': query}

    source = await discord.FFmpegOpusAudio.from_probe(url, **ffmpeg_options)

    vc.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(guild_id, interaction),
            bot.loop
        )
    )

    await interaction.followup.send(
        f"🎶 **Reproduciendo:** `{title}`",
        view=MusicButtons()
    )


# --- BOTONES ---
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
        guild_id = interaction.guild.id
        loop_mode[guild_id] = not loop_mode.get(guild_id, False)
        estado = "activado" if loop_mode[guild_id] else "desactivado"
        await interaction.response.send_message(f"🔁 Loop {estado}", ephemeral=True)

    @discord.ui.button(label="⏹ Detener", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        queue[guild_id] = []
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
        await interaction.response.send_message("⏹ Música detenida", ephemeral=True)


# --- SLASH COMMANDS ---
@tree.command(name="play", description="Reproduce una canción o URL")
async def play(interaction: discord.Interaction, *, query: str):
    await interaction.response.defer()
    guild_id = interaction.guild.id

    queue.setdefault(guild_id, [])
    loop_mode.setdefault(guild_id, False)

    vc = await join_vc(interaction)
    if vc is None:
        return

    if vc.is_playing() or vc.is_paused():
        queue[guild_id].append({'url': query})
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
    guild_id = interaction.guild.id
    queue[guild_id] = []
    vc = interaction.guild.voice_client
    if vc:
        vc.stop()
    await interaction.response.send_message("🛑 Música detenida y cola limpiada")


@tree.command(name="queue", description="Muestra la cola")
async def queue_cmd(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in queue or not queue[guild_id]:
        await interaction.response.send_message("📭 La cola está vacía")
    else:
        lista = "\n".join([f"{i+1}. {s['url']}" for i, s in enumerate(queue[guild_id])])
        await interaction.response.send_message(f"📜 **Cola:**\n{lista}")


@tree.command(name="leave", description="Desconecta al bot del canal de voz")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("❌ Desconectado.")


# --- AUTO-RECONEXIÓN ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id != bot.user.id:
        return

    guild = member.guild
    guild_id = guild.id
    vc = guild.voice_client

    # Bot desconectado manualmente
    if before.channel and not after.channel:
        print(f"⚠️ Bot desconectado de {guild.name}, intentando reconectar...")
        await asyncio.sleep(2)

        if now_playing.get(guild_id):
            try:
                if before.channel:
                    await before.channel.connect()
                    print(f"🔄 Reconectado en {guild.name}")
            except:
                print(f"❌ No se pudo reconectar en {guild.name}")


# LOOP QUE REPARA MÚSICA CAÍDA
async def autoreconnect_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            vc = guild.voice_client
            guild_id = guild.id

            if not vc:
                continue

            if not vc.is_playing() and now_playing.get(guild_id):
                print(f"🔧 Reparando reproducción en {guild.name}...")

                try:
                    url = now_playing[guild_id]['url']
                    await play_song(DummyInteraction(guild), url)
                except Exception as e:
                    print(f"❌ Error al reparar música en {guild.name}: {e}")

        await asyncio.sleep(5)


class DummyInteraction:
    def __init__(self, guild):
        self.guild = guild
        self.user = None
        self.followup = self

    async def send(self, *args, **kwargs):
        pass

    async def send_message(self, *args, **kwargs):
        pass

    async def defer(self):
        pass


bot.loop.create_task(autoreconnect_loop())


# --- READY ---
@bot.event
async def on_ready():
    print(f"✅ Conectado como {bot.user}")
    try:
        await tree.sync()
        print("✅ Slash commands sincronizados.")
    except Exception as e:
        print(f"❌ Error sincronizando: {e}")


bot.run(os.getenv("TOKEN"))
