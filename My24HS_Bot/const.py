import os
import requests
from discord import Color


# Config options
bot_token = 'INSERT_TOKEN_HERE'
commands_dir = os.path.join(os.path.curdir, 'commands')
attachments_dir = os.path.join(os.path.curdir, 'attachments')
# These roles are allowed to press the "Yes/No" buttons on the sysinfo prompt
sysinfo_allowed_roles = [
    # Members in Nvidia
    185774676969127936,
    # Mods in 24HS
    370559677949280257,
    # Feel Free to Ping in 24HS
    421504795988197377,
    # Helpdesk in Nvidia
    835499098886504509,
    # Admin role in my test server
    566274374014074886
]
# Color of the left bar in an Embed. Dark Red kinda fits the profile picture
embed_color = Color.dark_red()


def download_latest_nvidia_version() -> str:
    return '496.61'


def download_latest_amd_version() -> str:
    return '30.0.13033.5003'


system_manufacturer_unknown_values = [
    'To Be Filled By O.E.M.',
    'System manufacturer'
]
system_model_unknown_values = [
    'To Be Filled By O.E.M.',
    'System Product Name'
]
latest_nvidia_version = download_latest_nvidia_version()
latest_amd_version = download_latest_amd_version()
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

w11_build_to_version = {
    '22000': '21H2'
}
