import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import json
import os
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

DATA_FILE = "last_drops.json"
SUB_FILE = "subscribers.json"

# -------------------- DATA HELPERS --------------------
def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# -------------------- INITIAL DATA --------------------
drop_data = load_json(DATA_FILE, {"twitch": "", "kick": ""})
subs = load_json(SUB_FILE, {"users": []})

# -------------------- SCRAPING FUNCTIONS --------------------
def get_twitch_drop():
    url = "https://twitch.facepunch.com/"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        # Ajusta el selector según la página real
        drop = soup.find("h3")
        return drop.text.strip() if drop else None
    except Exception as e:
        print(f"[ERROR] Twitch scrape failed: {e}")
        return None

def get_kick_drop():
    url = "https://kick.facepunch.com/"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        # Ajusta el selector según la página real
        drop = soup.find("h3")
        return drop.text.strip() if drop else None
    except Exception as e:
        print(f"[ERROR] Kick scrape failed: {e}")
        return None

# -------------------- NOTIFY USERS --------------------
async def notify_users(embed):
    for user_id in subs["users"]:
        try:
            user = await bot.fetch_user(user_id)
            await user.send(embed=embed)
        except:
            pass

# -------------------- BOT EVENTS --------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    synced = await bot.tree.sync()
    print(f"Slash commands sincronizados: {len(synced)}")
    check_drops.start()

# -------------------- DROP LOOP --------------------
@tasks.loop(minutes=10)
async def check_drops():
    global drop_data
    channel = bot.get_channel(CHANNEL_ID)

    # TWITCH DROP
    twitch_drop = get_twitch_drop()
    if twitch_drop and twitch_drop != drop_data["twitch"]:
        drop_data["twitch"] = twitch_drop
        save_json(DATA_FILE, drop_data)
        embed = discord.Embed(
            title="🎮 Nuevo Twitch Drop de Rust",
            description=twitch_drop,
            color=0x9146FF
        )
        embed.add_field(name="Ver drops", value="https://twitch.facepunch.com/", inline=False)
        await channel.send(embed=embed)
        await notify_users(embed)

    # KICK DROP
    kick_drop = get_kick_drop()
    if kick_drop and kick_drop != drop_data["kick"]:
        drop_data["kick"] = kick_drop
        save_json(DATA_FILE, drop_data)
        embed = discord.Embed(
            title="🟢 Nuevo Kick Drop de Rust",
            description=kick_drop,
            color=0x53FC18
        )
        embed.add_field(name="Ver drops", value="https://kick.facepunch.com/", inline=False)
        await channel.send(embed=embed)
        await notify_users(embed)

# -------------------- SLASH COMMANDS --------------------
@bot.tree.command(name="drops", description="Ver drops activos de Rust")
async def drops(interaction: discord.Interaction):
    twitch_drop = get_twitch_drop() or "No se detecta ningún drop"
    kick_drop = get_kick_drop() or "No se detecta ningún drop"

    embed = discord.Embed(title="Rust Drops Activos", color=0xF47A20)
    embed.add_field(name="Twitch Drop", value=twitch_drop, inline=False)
    embed.add_field(name="Kick Drop", value=kick_drop, inline=False)
    embed.add_field(name="Links", value="https://twitch.facepunch.com/\nhttps://kick.facepunch.com/", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="forcecheck", description="Force check for new drops")
async def forcecheck(interaction: discord.Interaction):
    await interaction.response.send_message("🔍 Comprobando drops activos...")
    twitch_drop = get_twitch_drop() or "No se detecta ningún drop"
    kick_drop = get_kick_drop() or "No se detecta ningún drop"
    await interaction.followup.send(
        f"🎮 Twitch: {twitch_drop}\n🟢 Kick: {kick_drop}"
    )

@bot.tree.command(name="notify", description="Suscribirse o cancelar alertas de drops")
async def notify(interaction: discord.Interaction, mode: str):
    user_id = interaction.user.id
    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    mode = mode.lower()
    if mode == "on":
        if user_id not in subs["users"]:
            subs["users"].append(user_id)
            save_json(SUB_FILE, subs)
            await interaction.response.send_message("✅ Te has suscrito a las alertas de Rust drops", ephemeral=True)
        else:
            await interaction.response.send_message("Ya estás suscrito", ephemeral=True)
    elif mode == "off":
        if user_id in subs["users"]:
            subs["users"].remove(user_id)
            save_json(SUB_FILE, subs)
            await interaction.response.send_message("❌ Has cancelado las alertas", ephemeral=True)
        else:
            await interaction.response.send_message("No estabas suscrito", ephemeral=True)
    else:
        await interaction.response.send_message("Usa `/notify on` o `/notify off`", ephemeral=True)

# -------------------- START BOT --------------------
bot.run(TOKEN)