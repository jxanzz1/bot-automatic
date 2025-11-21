import disnake
from disnake.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
intents = disnake.Intents.all()

bot = commands.InteractionBot(intents=intents)

CHANNEL_ID = 1441472637217017946   # <-- Cambia esto


# --------------------------------------------------------
# Obtener enlace de audio
# --------------------------------------------------------
def get_audio(url: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "nocheckcertificate": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info["url"], info.get("title", "Audio")


# --------------------------------------------------------
# Botones del reproductor
# --------------------------------------------------------
class MusicButtons(disnake.ui.View):
    def __init__(self, voice):
        super().__init__(timeout=None)
        self.voice = voice

    @disnake.ui.button(label="⏸ Pausa", style=disnake.ButtonStyle.secondary)
    async def pause(self, button, inter):
        self.voice.pause()
        await inter.response.send_message("⏸ Pausado.", ephemeral=True)

    @disnake.ui.button(label="▶ Reanudar", style=disnake.ButtonStyle.success)
    async def resume(self, button, inter):
        self.voice.resume()
        await inter.response.send_message("▶ Reanudado.", ephemeral=True)

    @disnake.ui.button(label="⏭ Skip", style=disnake.ButtonStyle.primary)
    async def skip(self, button, inter):
        self.voice.stop()
        await inter.response.send_message("⏭ Saltado.", ephemeral=True)

    @disnake.ui.button(label="⛔ Stop", style=disnake.ButtonStyle.danger)
    async def stop(self, button, inter):
        self.voice.stop()
        await inter.response.send_message("⛔ Parado.", ephemeral=True)


# --------------------------------------------------------
# Mantenerse 24/7 en un canal de voz
# --------------------------------------------------------
@bot.event
async def on_ready():
    print("Bot iniciado.")

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        try:
            await channel.connect()
            print("Conectado 24/7 al canal.")
        except:
            pass


# --------------------------------------------------------
# SLASH COMMAND /play
# --------------------------------------------------------
@bot.slash_command(name="play", description="Reproduce música sin lavalink")
async def play(inter, query: str):
    await inter.response.defer()

    if not inter.author.voice:
        return await inter.edit_original_message("Debes estar en un canal de voz.")

    voice = inter.guild.voice_client
    if not voice:
        voice = await inter.author.voice.channel.connect()

    audio_url, title = get_audio(query)

    voice.stop()
    ffmpeg_opts = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    voice.play(
        disnake.FFmpegOpusAudio(audio_url, **ffmpeg_opts)
    )

    view = MusicButtons(voice)

    await inter.edit_original_message(
        f"🎶 Reproduciendo: **{title}**",
        view=view
    )


bot.run(os.getenv("TOKEN"))
