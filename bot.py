import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
import os

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "last_drops.json"
first_run = True


# =========================
# 💾 DATA
# =========================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"twitch_campaign_id": None, "kick_active": None}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"twitch_campaign_id": None, "kick_active": None}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


# =========================
# 🔎 TWITCH CHECK
# =========================
async def check_twitch_campaign():
    url = "https://gql.twitch.tv/gql"
    payload = [
        {
            "operationName": "ViewerDropsDashboard",
            "variables": {},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9a62a09b27c6c6d6dc0c6f216a73abdb0b3a0c7c0f2c92c38b0f81b190e0b8c9"
                }
            }
        }
    ]
    headers = {
        "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko",
        "Content-Type": "application/json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                campaigns = data[0]["data"]["currentUser"]["dropCampaignsInProgress"]
                for campaign in campaigns:
                    if "rust" in campaign["name"].lower():
                        return campaign["id"]
    except Exception as e:
        print("Error Twitch API:", e)
    return None


# =========================
# 🔎 KICK CHECK
# =========================
async def check_kick_active():
    url = "https://kick.facepunch.com/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.text()
                # Si el texto "Drops on Kick" está presente → activo
                active = "Drops on Kick" in html
                return active
    except Exception as e:
        print("Error Kick:", e)
        return None


# =========================
# 🔁 LOOP PRINCIPAL
# =========================
@tasks.loop(minutes=10)
async def check_drops():
    global first_run

    data = load_data()
    old_twitch_id = data.get("twitch_campaign_id")
    old_kick = data.get("kick_active")

    # ✅ obtener estado actual
    new_twitch_id = await check_twitch_campaign()
    new_kick = await check_kick_active()

    print(f"Twitch OLD: {old_twitch_id}, NEW: {new_twitch_id}")
    print(f"Kick OLD: {old_kick}, NEW: {new_kick}")

    # 🛑 primer arranque
    if first_run:
        save_data({"twitch_campaign_id": new_twitch_id, "kick_active": new_kick})
        first_run = False
        print("Primer arranque → guardando sin notificar")
        return

    # 🧠 CANAL DE DISCORD
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Canal no encontrado")
        return

    # =========================
    # 🔔 Twitch
    # =========================
    if old_twitch_id != new_twitch_id:
        save_data({"twitch_campaign_id": new_twitch_id, "kick_active": new_kick})
        if new_twitch_id:
            await channel.send("🟢 Nuevos drops de Rust en Twitch!")
        else:
            await channel.send("🔴 Los drops de Rust han terminado en Twitch")

    # =========================
    # 🔔 Kick
    # =========================
    if old_kick != new_kick:
        save_data({"twitch_campaign_id": new_twitch_id, "kick_active": new_kick})
        if new_kick:
            await channel.send("🟢 Nuevos drops de Rust en Kick!")
        else:
            await channel.send("🔴 Los drops de Rust han terminado en Kick")


# =========================
# 🤖 BOT READY
# =========================
@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    await asyncio.sleep(30)  # evita falsos positivos al arrancar
    check_drops.start()


# =========================
# 💬 COMANDO MANUAL
# =========================
@bot.command()
async def drops(ctx):
    twitch = await check_twitch_campaign()
    kick = await check_kick_active()

    msg = ""
    msg += "🟢 Twitch activo\n" if twitch else "🔴 Twitch inactivo\n"
    msg += "🟢 Kick activo\n" if kick else "🔴 Kick inactivo"

    await ctx.send(msg)


# =========================
# ▶️ RUN
# =========================
bot.run(TOKEN)