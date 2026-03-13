import discord
from discord.ext import commands, tasks
import requests
import json
import os
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ROLE_ID = int(os.getenv("ROLE_ID", 0))  # opcional para rol de notificación

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

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

drop_data = load_json(DATA_FILE, {"twitch": {}, "kick": {}})
subs = load_json(SUB_FILE, {"users": []})

# -------------------- API FUNCTIONS --------------------

def get_campaigns(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data
    except:
        pass
    return []

# -------------------- BOT EVENTS --------------------

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

# -------------------- DROP LOOP --------------------

@tasks.loop(seconds=30)
async def check_drops():
    global drop_data
    channel = bot.get_channel(CHANNEL_ID)

    twitch_campaigns = get_campaigns("https://twitch.facepunch.com/api/campaigns")
    kick_campaigns = get_campaigns("https://kick.facepunch.com/api/campaigns")

    # TWITCH DROPS
    if twitch_campaigns:
        latest = twitch_campaigns[0]
        if latest.get('id') != drop_data.get("twitch", {}).get('id'):
            drop_data["twitch"] = latest
            save_json(DATA_FILE, drop_data)

            embed = discord.Embed(
                title="🎮 Nuevo Twitch Drop detectado",
                description=latest.get('name', 'Evento Rust'),
                color=0x9146FF
            )
            embed.add_field(name="Ver drops", value="https://twitch.facepunch.com/", inline=False)
            embed.set_footer(text="Rust Drops Tracker")

            if channel:
                await channel.send(embed=embed)

            await notify_users(embed)

    # KICK DROPS
    if kick_campaigns:
        latest = kick_campaigns[0]
        if latest.get('id') != drop_data.get("kick", {}).get('id'):
            drop_data["kick"] = latest
            save_json(DATA_FILE, drop_data)

            embed = discord.Embed(
                title="🟢 Nuevo Kick Drop detectado",
                description=latest.get('name', 'Evento Rust'),
                color=0x53FC18
            )
            embed.add_field(name="Ver drops", value="https://kick.facepunch.com/", inline=False)
            embed.set_footer(text="Rust Drops Tracker")

            if channel:
                await channel.send(embed=embed)

            await notify_users(embed)

# -------------------- NOTIFY USERS --------------------

async def notify_users(embed):
    for user_id in subs["users"]:
        try:
            user = await bot.fetch_user(user_id)
            await user.send(embed=embed)
        except:
            pass

# -------------------- SLASH COMMANDS --------------------

@bot.tree.command(name="notify", description="Suscribirse o cancelar alertas de drops")
async def notify(interaction: discord.Interaction, mode: str):
    user_id = interaction.user.id
    member = interaction.user if isinstance(interaction.user, discord.Member) else None

    if mode.lower() == "on":
        if user_id not in subs["users"]:
            subs["users"].append(user_id)
            save_json(SUB_FILE, subs)
            # Añadir rol si ROLE_ID está definido
            if ROLE_ID and member and member.guild:
                role = member.guild.get_role(ROLE_ID)
                if role:
                    await member.add_roles(role)
        await interaction.response.send_message("🔔 Te has suscrito a las alertas de Rust drops", ephemeral=True)

    elif mode.lower() == "off":
        if user_id in subs["users"]:
            subs["users"].remove(user_id)
            save_json(SUB_FILE, subs)
            if ROLE_ID and member and member.guild:
                role = member.guild.get_role(ROLE_ID)
                if role:
                    await member.remove_roles(role)
        await interaction.response.send_message("🔕 Has cancelado las alertas", ephemeral=True)

    else:
        await interaction.response.send_message("Usa `/notify on` o `/notify off`", ephemeral=True)

@bot.tree.command(name="drops", description="Ver drops activos de Rust")
async def drops(interaction: discord.Interaction):
    twitch_campaigns = get_campaigns("https://twitch.facepunch.com/api/campaigns")
    kick_campaigns = get_campaigns("https://kick.facepunch.com/api/campaigns")

    embed = discord.Embed(title="Rust Drops Activos", color=0xF47A20)

    if twitch_campaigns:
        names = [c.get('name') for c in twitch_campaigns[:5]]
        embed.add_field(name="Twitch Drops", value='\n'.join(names), inline=False)

    if kick_campaigns:
        names = [c.get('name') for c in kick_campaigns[:5]]
        embed.add_field(name="Kick Drops", value='\n'.join(names), inline=False)

    embed.add_field(name="Links", value="https://twitch.facepunch.com/\nhttps://kick.facepunch.com/", inline=False)
    await interaction.response.send_message(embed=embed)

# -------------------- START BOT --------------------

bot.run(TOKEN)