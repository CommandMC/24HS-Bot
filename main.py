import discord
import logging

from My24HS_Bot.bot import My24HSbot
from My24HS_Bot.const import bot_token

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s/%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    client = My24HSbot(intents=discord.Intents.all(), command_prefix='')
    client.run(bot_token)
