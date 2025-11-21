import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=";", intents=intents)

class VoiceButtons(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client is None:
            await self.channel.connect()
            await interaction.response.send_message("🔊 El bot se unió al canal y estará 24/7.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Ya estoy conectado.", ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect(force=True)
            await interaction.response.send_message("👋 El bot salió del canal.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No estoy en ningún canal.", ephemeral=True)


@bot.tree.command(name="join", description="El bot entra a tu canal de voz y se queda 24/7")
async def join_cmd(interaction: discord.Interaction):
    channel = interaction.user.voice.channel if interaction.user.voice else None

    if channel is None:
        return await interaction.response.send_message(
            "⚠️ Debes estar en un canal de voz.", ephemeral=True
        )

    view = VoiceButtons(channel)
    await interaction.response.send_message(
        f"Selecciona una opción para el canal: **{channel.name}**",
        view=view,
        ephemeral=True
    )


# Mantener vivo 24/7 (reconexión si se cae)
async def stay_24_7():
    await bot.wait_until_ready()

    while not bot.is_closed():
        for guild in bot.guilds:
            vc = guild.voice_client
            if vc and not vc.is_connected():
                try:
                    await vc.connect()
                except:
                    pass
        await asyncio.sleep(10)


@bot.event
async def on_ready():
    print(f"Bot listo como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

    bot.loop.create_task(stay_24_7())


bot.run(os.getenv("TOKEN"))
