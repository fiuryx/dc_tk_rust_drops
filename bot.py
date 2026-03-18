import discord
from discord.ext import tasks
from discord import app_commands
import aiohttp
import asyncio
import json
import os
from bs4 import BeautifulSoup
from aiohttp import web

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

if not TOKEN or CHANNEL_ID == 0:
    raise ValueError("Faltan variables de entorno")

intents = discord.Intents.default()
intents.message_content = True

DATA_FILE = "last_drops.json"
first_run = True

# =========================
# 💾 DATA
# =========================
def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            return {"twitch": None, "kick": None}
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"twitch": None, "kick": None}


def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Error guardando:", e)

# =========================
# 🌐 SESSION
# =========================
session = None

async def get_session():
    global session
    if session is None or session.closed:
        timeout = aiohttp.ClientTimeout(total=15)
        session = aiohttp.ClientSession(timeout=timeout)
    return session

# =========================
# 🔎 TWITCH
# =========================
async def check_twitch():
    try:
        session = await get_session()
        async with session.get("https://twitch.facepunch.com/") as resp:
            if resp.status != 200:
                return None

            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            h1 = soup.find("h1", class_="title hero-title")

            if not h1:
                return None

            text = h1.get_text(strip=True)
            return "Drops on Twitch" not in text

    except Exception as e:
        print("Error Twitch:", e)
        return None

# =========================
# 🔎 KICK
# =========================
async def check_kick():
    try:
        session = await get_session()
        async with session.get("https://kick.facepunch.com/") as resp:
            if resp.status != 200:
                return None

            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            h1 = soup.find("h1", class_="title hero-title")

            if not h1:
                return None

            text = h1.get_text(strip=True)
            return "Drops on Kick" not in text

    except Exception as e:
        print("Error Kick:", e)
        return None

# =========================
# 🌐 WEB SERVER (ANTI 502)
# =========================
async def handle(request):
    return web.Response(text="OK")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# =========================
# 🤖 BOT
# =========================
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        @self.tree.command(name="drops", description="Ver estado de drops")
        async def drops_command(interaction: discord.Interaction):
            twitch = await check_twitch()
            kick = await check_kick()

            msg = []
            msg.append("🟢 Twitch" if twitch else "🔴 Twitch")
            msg.append("🟢 Kick" if kick else "🔴 Kick")

            await interaction.response.send_message("\n".join(msg))

        await self.tree.sync()
        print("Comando /drops sincronizado")

bot = MyBot()

# =========================
# ❌ IGNORAR ERROR DISCORD
# =========================
@bot.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, discord.app_commands.errors.CommandNotFound):
        return
    print(f"Error comando: {error}")

# =========================
# 🔁 LOOP
# =========================
@tasks.loop(minutes=10)
async def check_drops():
    global first_run

    data = load_data()
    old_twitch = data.get("twitch")
    old_kick = data.get("kick")

    new_twitch = await check_twitch()
    new_kick = await check_kick()

    print(f"Twitch: {old_twitch} → {new_twitch}")
    print(f"Kick: {old_kick} → {new_kick}")

    if first_run:
        save_data({"twitch": new_twitch, "kick": new_kick})
        first_run = False
        print("Primer run ignorado")
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    if new_twitch != old_twitch:
        await channel.send(
            "🟢 Drops activos en Twitch" if new_twitch else "🔴 Drops terminados en Twitch"
        )

    if new_kick != old_kick:
        await channel.send(
            "🟢 Drops activos en Kick" if new_kick else "🔴 Drops terminados en Kick"
        )

    save_data({"twitch": new_twitch, "kick": new_kick})

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")

    await start_webserver()  # 🔥 evita 502
    check_drops.start()

# =========================
# RUN
# =========================
bot.run(TOKEN)