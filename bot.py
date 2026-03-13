import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

DATA_FILE = "last_drops.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"twitch": "", "kick": ""}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def get_drop(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    drop = soup.find("h3")
    if drop:
        return drop.text.strip()

    return None

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    check_drops.start()

@tasks.loop(minutes=10)
async def check_drops():
    global data

    channel = bot.get_channel(CHANNEL_ID)

    twitch = get_drop("https://twitch.facepunch.com/")
    kick = get_drop("https://kick.facepunch.com/")

    if twitch and twitch != data["twitch"]:
        data["twitch"] = twitch
        save_data(data)

        await channel.send(
            "🎮 **Nuevo Twitch Drop de Rust detectado!**\nhttps://twitch.facepunch.com/"
        )

    if kick and kick != data["kick"]:
        data["kick"] = kick
        save_data(data)

        await channel.send(
            "🟢 **Nuevo Kick Drop de Rust detectado!**\nhttps://kick.facepunch.com/"
        )

bot.run(TOKEN)