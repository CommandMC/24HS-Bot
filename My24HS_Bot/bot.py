import asyncio
import discord
import discord_slash
import logging
import os
from discord import File, Message, Member
from discord.ext.commands import Bot, Context
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from io import BytesIO, StringIO

from My24HS_Bot.const import commands_dir, sysinfo_allowed_roles
from My24HS_Bot.util import parse_sysinfo, is_sysinfo, convert_utf16_utf8


# Python doesn't allow classes to start with a number, so we have to add a "My" to the start of this
class My24HSbot(Bot):
    def __init__(self, **options):
        super().__init__(**options)
        self.shash_handler = discord_slash.SlashCommand(self)
        self.logger = logging.getLogger('24HS-Bot')

    async def on_ready(self):
        # Add and sync slash commands
        await self.sync_commands()
        # Add discord_components to the bot (to be able to use Buttons)
        DiscordComponents(self)
        self.logger.info('on_ready finished, logged in as {}'.format(self.user))

    async def on_guild_join(self):
        await self.sync_commands()

    async def on_guild_remove(self):
        await self.sync_commands()

    async def on_message(self, message: discord.Message):
        # Ignore special messages (like member joins or nitro boosts)
        if message.type is not discord.MessageType.default:
            return
        # Ignore messages we send ourselves
        if message.author == self.user:
            return
        # Ignore messages without any attachments
        if not message.attachments:
            return
        for attachment in message.attachments:
            if not attachment.filename.endswith('.txt'):
                self.logger.debug('Got an attachment, but it\'s not a text file')
                continue
            if not attachment.content_type.endswith('UTF-16'):
                self.logger.debug('Got an attachment that is a text file, but it\'s not UTF-16-encoded')
                continue

            self.logger.debug('Got a UTF-16 encoded text file. This might be a sysinfo!')
            # Save the file into memory
            temp_storage = BytesIO()
            await attachment.save(temp_storage)
            utf8_sysinfo = convert_utf16_utf8(temp_storage)
            if not is_sysinfo(utf8_sysinfo):
                self.logger.debug('Text file turned out to not be a sysinfo file.')
                continue
            await self.handle_sysinfo(utf8_sysinfo, message, attachment)

    async def handle_sysinfo(self, utf8_sysinfo: StringIO, message, attachment):
        self.logger.info(
            'Asking if sysinfo file in #{} (sent by {}) should be parsed'.format(message.channel, message.author)
        )
        yes_button = Button(label='Yes', style=ButtonStyle.green)
        no_button = Button(label='No', style=ButtonStyle.red)
        msg: Message
        msg = await message.channel.send(
            content='A sysinfo file was detected! Do you want to run QuickDiagnose?',
            components=[yes_button, no_button]
        )
        try:
            interaction = await self.wait_for('button_click', check=lambda x: button_check(x, msg), timeout=600)
        except asyncio.TimeoutError:
            await msg.delete()
            return
        if interaction.component.label == 'No':
            await msg.delete()
            return
        await interaction.respond(
            type=InteractionType.DeferredUpdateMessage
        )
        info, quickdiagnosis = parse_sysinfo(utf8_sysinfo)
        file_to_attach = File(
            fp=utf8_sysinfo,
            filename='.'.join(attachment.filename.split('.')[:-1]) + '_utf8.txt'
        )
        await message.channel.send(
            embed=info
        )
        if quickdiagnosis.description != '':
            await message.channel.send(
                embed=quickdiagnosis
            )
        await message.channel.send(
            content='Sysinfo file in UTF-8 encoding:',
            file=file_to_attach
        )
        self.logger.info('Parsed sysinfo file in #{} (sent by {})'.format(message.channel, message.author))
        await msg.delete()

    async def sync_commands(self):
        # Go through the commands
        for file_or_folder in os.listdir(commands_dir):
            if not os.path.isfile(os.path.join(commands_dir, file_or_folder)):
                continue
            filename, fileext = os.path.splitext(file_or_folder)
            # The first line of the file is the command description, everything after that is the message that gets sent
            with open(os.path.join(commands_dir, file_or_folder)) as f:
                command_desc = f.readline()
            # If there is actually a description (Discord errors out if there isn't AFAIK), add the command
            # As to what happens when the command is ran, that's handled in 'handle_command'
            if command_desc is not None:
                self.shash_handler.add_slash_command(
                    cmd=self.handle_command,
                    name=filename,
                    description=command_desc,
                    guild_ids=list(guild.id for guild in self.guilds)
                )
        # Once all commands are added, push them to Discord
        # This might not be necessary anymore, but I've found that without it some commands don't update immediately
        await self.shash_handler.sync_all_commands()

    def get_command_resp(self, command: str):
        self.logger.debug('Getting command response for {}'.format(command))
        file_path = os.path.join(commands_dir, command + '.txt')
        if not os.path.isfile(file_path):
            logging.warning('Command ' + command + ' does not exist!')
            return
        with open(file_path) as f:
            # The first line of the file is the description, so we'll return every line after that
            return f.readlines()[1:]

    async def handle_command(self, ctx: Context):
        self.logger.info('{} used /{} in #{}'.format(ctx.author, ctx.command, ctx.channel))
        response = self.get_command_resp(ctx.command)
        if response:
            await ctx.send(''.join(response))
            return
        await ctx.send('No response found')


def button_check(ctx, msg: Message) -> bool:
    # So, this gets ran whenever any button gets pressed. This creates an issue when two functions are waiting for a
    # button press at the same time, since both recieve the same event, but only one should of course be triggered.
    # Because of that, we have to also check if the message ID of the message we initially sent out (the one which has
    # the buttons on it) and the message ID of the message where a button was being pressed are the same
    # I hope this made sense
    if msg.id != ctx.message.id:
        return False
    # Always allow button presses when in DMs/Groups
    if not ctx.guild:
        return True
    member: Member = ctx.guild.get_member(ctx.user.id)
    if not member:
        return False
    for role in member.roles:
        if role.id in sysinfo_allowed_roles:
            return True
    return False
