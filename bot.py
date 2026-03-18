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
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

if not TOKEN or CHANNEL_ID == 0:
    raise ValueError("Faltan variables de entorno")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "last_drops.json"
first_run = True


# =========================
# 💾 DATA SAFE
# =========================
def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            return {"twitch_campaign_id": None, "kick_active": None}
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"twitch_campaign_id": None, "kick_active": None}


def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Error guardando datos:", e)


# =========================
# 🌐 SESSION GLOBAL (PRO)
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
async def check_twitch_campaign():
    try:
        session = await get_session()

        url = "https://gql.twitch.tv/gql"

        payload = [{
            "operationName": "ViewerDropsDashboard",
            "variables": {},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9a62a09b27c6c6d6dc0c6f216a73abdb0b3a0c7c0f2c92c38b0f81b190e0b8c9"
                }
            }
        }]

        headers = {
            "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            "Content-Type": "application/json"
        }

        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                print("Twitch status:", resp.status)
                return None

            data = await resp.json()

            campaigns = data[0]["data"]["currentUser"]["dropCampaignsInProgress"]

            for c in campaigns:
                if "rust" in c["name"].lower():
                    return c["id"]

    except Exception as e:
        print("Error Twitch:", e)

    return None


# =========================
# 🔎 KICK
# =========================
async def check_kick_active():
    try:
        session = await get_session()
        url = "https://kick.facepunch.com/"

        async with session.get(url) as resp:
            if resp.status != 200:
                print("Kick status:", resp.status)
                return None

            html = await resp.text()
            return "Drops on Kick" in html

    except Exception as e:
        print("Error Kick:", e)
        return None


# =========================
# 🔁 LOOP PRO
# =========================
@tasks.loop(minutes=10)
async def check_drops():
    global first_run

    try:
        data = load_data()

        old_twitch = data.get("twitch_campaign_id")
        old_kick = data.get("kick_active")

        new_twitch = await check_twitch_campaign()
        new_kick = await check_kick_active()

        print(f"Twitch: {old_twitch} → {new_twitch}")
        print(f"Kick: {old_kick} → {new_kick}")

        # ❌ evitar datos corruptos
        if new_twitch is None and new_kick is None:
            print("Sin datos válidos → skip")
            return

        # 🛑 primer run
        if first_run:
            save_data({
                "twitch_campaign_id": new_twitch,
                "kick_active": new_kick
            })
            first_run = False
            print("Primer run ignorado")
            return

        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print("Canal no encontrado")
            return

        # =========================
        # TWITCH
        # =========================
        if new_twitch != old_twitch:
            if new_twitch:
                await channel.send("🟢 Drops de Rust activos en Twitch")
            else:
                await channel.send("🔴 Drops de Rust terminados en Twitch")

        # =========================
        # KICK
        # =========================
        if new_kick != old_kick:
            if new_kick:
                await channel.send("🟢 Drops de Rust activos en Kick")
            else:
                await channel.send("🔴 Drops de Rust terminados en Kick")

        save_data({
            "twitch_campaign_id": new_twitch,
            "kick_active": new_kick
        })

    except Exception as e:
        print("Error loop:", e)


# =========================
# READY
# =========================
@bot.event
async def on_ready():
    print(f"Bot listo: {bot.user}")
    await asyncio.sleep(20)
    check_drops.start()


# =========================
# COMANDO
# =========================
@bot.command()
async def drops(ctx):
    twitch = await check_twitch_campaign()
    kick = await check_kick_active()

    msg = []
    msg.append("🟢 Twitch" if twitch else "🔴 Twitch")
    msg.append("🟢 Kick" if kick else "🔴 Kick")

    await ctx.send("\n".join(msg))


# =========================
# RUN (SIN BUCLES RAROS)
# =========================
bot.run(TOKEN, reconnect=False)