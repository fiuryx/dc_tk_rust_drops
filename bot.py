import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "last_drops.json"
SUB_FILE = "subscribers.json"


def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


data = load_json(DATA_FILE, {
    "twitch": {"active": False, "hash": "", "campaign": ""},
    "kick": {"active": False, "hash": ""}
})

subs = load_json(SUB_FILE, {"users": []})


# ---------------- SCRAPER FACEPUNCH ----------------

def scrape_page(url, inactive_text):

    try:

        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        page_text = soup.get_text()

        active = inactive_text not in page_text

        content = ""
        for h in soup.find_all(["h2", "h3", "h4"]):
            content += h.text.strip()

        content_hash = str(hash(content))

        return {
            "active": active,
            "hash": content_hash
        }

    except Exception as e:
        print(f"[SCRAPER ERROR] {e}")
        return None


def get_twitch_page():
    return scrape_page(
        "https://twitch.facepunch.com/",
        "Drops on Twitch"
    )


def get_kick_page():
    return scrape_page(
        "https://kick.facepunch.com/",
        "Drops on Kick"
    )


# ---------------- TWITCH CAMPAIGN DETECTION ----------------

def check_twitch_campaign():

    try:

        url = "https://gql.twitch.tv/gql"

        headers = {
            "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko"
        }

        query = [{
            "operationName": "ViewerDropsDashboard",
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "eecb0f8f36fcd1a89d5dbe5a7ab6b5234f6b31d911cfef95c0d37db114d4e2a1"
                }
            }
        }]

        r = requests.post(url, json=query, headers=headers, timeout=10)

        campaigns = r.json()[0]["data"]["currentUser"]["dropCampaignsInProgress"]

        for c in campaigns:

            name = c["name"].lower()

            if "rust" in name:

                return c["id"]

        return None

    except Exception as e:

        print("[TWITCH CAMPAIGN ERROR]", e)

        return None


# ---------------- NOTIFY USERS ----------------

async def notify_users(embed):

    for user_id in subs["users"]:

        try:

            user = await bot.fetch_user(user_id)
            await user.send(embed=embed)

        except:
            pass


# ---------------- BOT READY ----------------

@bot.event
async def on_ready():

    print(f"Bot conectado como {bot.user}")

    synced = await bot.tree.sync()
    print(f"{len(synced)} comandos sincronizados")

    check_drops.start()


# ---------------- DROP LOOP ----------------

@tasks.loop(minutes=10)
async def check_drops():

    global data

    channel = bot.get_channel(CHANNEL_ID)

    twitch_page = get_twitch_page()
    kick_page = get_kick_page()

    twitch_campaign = check_twitch_campaign()

    # TWITCH DETECTION

    if (
        twitch_page and
        (
            twitch_page["active"] != data["twitch"]["active"]
            or twitch_page["hash"] != data["twitch"]["hash"]
            or twitch_campaign != data["twitch"]["campaign"]
        )
    ):

        data["twitch"]["active"] = twitch_page["active"]
        data["twitch"]["hash"] = twitch_page["hash"]
        data["twitch"]["campaign"] = twitch_campaign

        save_json(DATA_FILE, data)

        embed = discord.Embed(
            title="🎮 Cambio detectado en Twitch Drops",
            description="Puede haber nuevos drops activos",
            color=0x9146FF
        )

        embed.add_field(
            name="Ver Drops",
            value="https://twitch.facepunch.com/",
            inline=False
        )

        await channel.send(embed=embed)
        await notify_users(embed)

    # KICK DETECTION

    if kick_page and (
        kick_page["active"] != data["kick"]["active"]
        or kick_page["hash"] != data["kick"]["hash"]
    ):

        data["kick"] = kick_page
        save_json(DATA_FILE, data)

        embed = discord.Embed(
            title="🟢 Cambio detectado en Kick Drops",
            description="Puede haber nuevos drops activos",
            color=0x00FF7F
        )

        embed.add_field(
            name="Ver Drops",
            value="https://kick.facepunch.com/",
            inline=False
        )

        await channel.send(embed=embed)
        await notify_users(embed)


# ---------------- COMMANDS ----------------

@bot.tree.command(name="drops", description="Ver estado actual de drops")
async def drops(interaction: discord.Interaction):

    twitch = get_twitch_page()
    kick = get_kick_page()

    embed = discord.Embed(
        title="Estado actual de Rust Drops",
        color=0xF47A20
    )

    embed.add_field(
        name="Twitch",
        value="🟢 Activo" if twitch and twitch["active"] else "🔴 Inactivo"
    )

    embed.add_field(
        name="Kick",
        value="🟢 Activo" if kick and kick["active"] else "🔴 Inactivo"
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="forcecheck", description="Forzar comprobación de drops")
async def forcecheck(interaction: discord.Interaction):

    await interaction.response.send_message("🔍 Comprobando drops...")
    await check_drops()


@bot.tree.command(name="notify", description="Suscribirse o cancelar alertas")
async def notify(interaction: discord.Interaction, mode: str):

    user_id = interaction.user.id
    mode = mode.lower()

    if mode == "on":

        if user_id not in subs["users"]:
            subs["users"].append(user_id)
            save_json(SUB_FILE, subs)

            await interaction.response.send_message(
                "Te has suscrito a las alertas de drops",
                ephemeral=True
            )

    elif mode == "off":

        if user_id in subs["users"]:
            subs["users"].remove(user_id)
            save_json(SUB_FILE, subs)

            await interaction.response.send_message(
                "Te has desuscrito",
                ephemeral=True
            )


bot.run(TOKEN)