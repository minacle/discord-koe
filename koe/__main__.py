from __future__ import annotations

from . import auth
from .auth import Auth
from .bot import Bot

import discord
from dotenv import load_dotenv
from sys import exit

if __name__ != "__main__":
    exit()


load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = Bot(
    intents=intents,
    auth=Auth(discord=auth.Discord(), google=auth.Google(), vom=auth.VOM())
)
bot.run()
