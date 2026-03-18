import discord
from discord.ext import tasks
from discord import app_commands
import asyncio
import os
import json
from playwright.async_api import async_playwright
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
# 🌐 PLAYWRIGHT OPTIMIZADO
# =========================
playwright_instance = None
browser = None
page = None

async def init_browser():
    global playwright_instance, browser, page
    playwright_instance = await async_playwright().start()
    browser = await playwright_instance.chromium.launch(headless=True)
    page = await browser.new_page()

async def close_browser():
    await page.close()
    await browser.close()
    await playwright_instance.stop()

async def check_page(url):
    """
    Devuelve True si hay drops activos, False si no
    """
    max_retries = 2
    for attempt in range(max_retries):
        try:
            await page.goto(url, timeout=60000)
            # Esperar a que un elemento de drop real aparezca o el DOM se cargue
            await page.wait_for_selector("h1.title.hero-title", timeout=5000)
            content = await page.content()

            # Lógica simple: si "Drops on" está presente en el <h1>, no hay drops activos
            h1_text = await page.inner_text("h1.title.hero-title")
            if "Drops on" in h1_text:
                return False
            else:
                return True
        except Exception as e:
            print(f"Intento {attempt+1} fallido para {url}: {e}")
            await asyncio.sleep(2)
    return None  # fallo total

async def check_twitch():
    return await check_page("https://twitch.facepunch.com/")

async def check_kick():
    return await check_page("https://kick.facepunch.com/")

# =========================
# 🌐 WEB SERVER
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

    await init_browser()        # 🔥 inicia Playwright
    await start_webserver()     # 🔥 webserver para Railway
    check_drops.start()

# =========================
# RUN
# =========================
try:
    bot.run(TOKEN)
finally:
    asyncio.run(close_browser())