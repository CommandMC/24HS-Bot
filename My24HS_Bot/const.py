import os
import requests
from discord import Color


# Config options
bot_token = 'INSERT_TOKEN_HERE'
commands_dir = os.path.join(os.path.curdir, 'commands')
# These roles are allowed to press the "Yes/No" buttons on the sysinfo prompt
sysinfo_allowed_roles = [
    # Feel Free to Ping in 24HS
    421504795988197377,
    # Helpdesk in Nvidia
    835499098886504509
]
# Color of the left bar in an Embed. Dark Red kinda fits the profile picture
embed_color = Color.dark_red()


def download_latest_nvidia_version() -> str:
    req = requests.get('https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/nvidiaGPU.txt')
    if req.status_code == 200:
        return req.text.splitlines()[0]
    else:
        raise ConnectionError


system_manufacturer_unknown_values = [
    'To Be Filled By O.E.M.',
    'System manufacturer'
]
latest_nvidia_version = download_latest_nvidia_version()
w10_build_to_version = {
    '10240': '1507',
    '10586': '1511',
    '14393': '1607',
    '15063': '1703',
    '16299': '1709',
    '17134': '1803',
    '17763': '1809',
    '18362': '1903',
    '18363': '1909',
    '19041': '2004',
    '19042': '20H2',
    '19043': '21H1'
}
