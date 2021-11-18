import asyncio
import logging
import os
import traceback
from io import StringIO
from typing import Union

import discord
import discord_slash
import yaml
from discord import File, Message, Member, Guild, Embed, Activity, ActivityType, User
from discord.ext.commands import Bot
from discord_slash import ButtonStyle, ComponentContext, SlashContext
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component

from My24HS_Bot.const import commands_dir, sysinfo_allowed_roles, embed_color, attachments_dir
from My24HS_Bot.util import handle_sysinfo, download_sysinfo


# Python doesn't allow classes to start with a number, so we have to add a "My" to the start of this
class My24HSbot(Bot):
    def __init__(self, **options):
        super().__init__(**options)
        self.shash_handler = discord_slash.SlashCommand(self)
        self.logger = logging.getLogger('24HS-Bot')
        self.commands_list: dict = {}
        self.has_added_commands = False

    async def on_ready(self):
        await self.change_presence(activity=Activity(name='DanielIsCool.txt', type=ActivityType.watching))
        # on_ready is called when the bot starts and when it reconnects. Thus, we can't just add the commands
        # every time we're in here, since that will error out with duplicate command warnings
        if self.has_added_commands:
            return
        # Add and sync slash commands
        await self.add_commands()
        self.logger.info('on_ready finished, logged in as {}'.format(self.user))
        self.has_added_commands = True

    async def on_guild_join(self, guild: Guild):
        self.logger.info('Joined a guild! {}'.format(guild.name))
        await self.add_commands([guild.id])

    async def on_guild_remove(self, guild: Guild):
        self.logger.info('Left a guild! {}'.format(guild.name))
        await self.add_commands([guild.id])

    async def on_message(self, message: discord.Message):
        if not self.is_interesting_message(message):
            return

        # I don't think it's possible for regular users to attach more than one text file to a message, so doing [0]
        # here should be fine
        sysinfo_attachment = message.attachments[0]

        # For some reason some attachment files can just not have a file name?
        if not sysinfo_attachment.filename:
            return

        # Ignore non-text attachments and text attachments that aren't UTF-16
        if not sysinfo_attachment.filename.endswith('.txt') and not sysinfo_attachment.content_type.endswith('UTF-16'):
            return

        self.logger.debug('Got a UTF-16 encoded text file. This might be a sysinfo!')
        utf8_sysinfo_or_false = await download_sysinfo(sysinfo_attachment)
        if not utf8_sysinfo_or_false:
            self.logger.debug('Text file turned out to not be a sysinfo file.')
            return

        filename_without_extension = '.'.join(sysinfo_attachment.filename.split('.')[:-1])
        new_filename = filename_without_extension + '_utf8.txt'
        await self.handle_sysinfo(utf8_sysinfo_or_false, message, new_filename)

    async def handle_sysinfo(self, utf8_sysinfo: StringIO, message, filename: str):
        self.logger.info(
            'Asking if sysinfo file in #{} (sent by {}) should be parsed'.format(message.channel, message.author)
        )
        action_row = create_actionrow(
            create_button(label='Yes', style=ButtonStyle.green),
            create_button(label='No', style=ButtonStyle.red)
        )
        msg: Message
        msg = await message.channel.send(
            content='A sysinfo file was detected! Do you want to run QuickDiagnose?\n\n'
                    'Note: Only tech support can press the buttons',
            components=[action_row]
        )
        try:
            interaction: ComponentContext = await wait_for_component(
                self,
                components=action_row,
                timeout=600,
                check=button_check
            )
        except asyncio.TimeoutError:
            await msg.delete()
            return

        if interaction.component['label'] == 'No':
            await msg.delete()
            return

        await interaction.edit_origin(
            content='Parsing Sysinfo...',
            components=None
        )

        async with interaction.channel.typing():
            try:
                info, quickdiagnosis = handle_sysinfo(utf8_sysinfo)
            except Exception as e:
                await message.channel.send(
                    content='There was an issue parsing this sysinfo file \\:( \n```\n' +
                            ''.join(traceback.format_exception(type(e), e, e.__traceback__)) + '```',
                    delete_after=30.0
                )
                await msg.delete()
                self.logger.info(
                    'Failed to parse sysinfo file: \n' +
                    ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                )
                return
            await message.channel.send(
                embed=info
            )
            if quickdiagnosis.description != '':
                await message.channel.send(
                    embed=quickdiagnosis
                )
            # Check if the file size is more than 8MB
            utf8_sysinfo.seek(0, os.SEEK_END)
            if utf8_sysinfo.tell() <= 8000000:
                utf8_sysinfo.seek(0)
                await message.channel.send(
                    content='Sysinfo file in UTF-8 encoding:',
                    file=File(fp=utf8_sysinfo, filename=filename)
                )
        self.logger.info('Parsed sysinfo file in #{} (sent by {})'.format(message.channel, message.author))
        await msg.delete()

    def read_commands(self):
        for file_or_folder in os.listdir(commands_dir):
            if not os.path.isfile(os.path.join(commands_dir, file_or_folder)):
                continue

            filename, fileext = os.path.splitext(file_or_folder)
            if fileext != '.yml':
                continue

            with open(os.path.join(commands_dir, file_or_folder)) as f:
                self.commands_list[filename] = yaml.safe_load(f)

    async def add_commands(self, guilds: list[Guild] = None):
        # If specific guilds aren't specified, use all guilds
        if guilds is None:
            guilds = self.guilds

        guild_ids = list(guild.id for guild in guilds)
        # If we don't have commands stored yet, read them in
        if not self.commands_list:
            self.read_commands()

        for command_name, command_info in self.commands_list.items():
            # If the command is a copy, replace all the info (description etc.) with the original one's
            if command_info.get('copy_of'):
                self.logger.debug('Command {} is a copy of {}'.format(command_name, command_info.get('copy_of')))
                command_info = self.commands_list[command_info.get('copy_of')]

            self.shash_handler.add_slash_command(
                cmd=self.handle_command,
                name=command_name,
                description=command_info.get('description'),
                guild_ids=guild_ids,
                options=[
                    create_option(
                        name='noinline',
                        description='Disable inline links in message',
                        option_type=5,
                        required=False
                    ),
                    create_option(
                        name='mention',
                        description='Specify a user to ping with the command',
                        option_type=6,
                        required=False
                    )
                ]
            )
        # Once all commands are added, push them to Discord
        # This might not be necessary anymore, but I've found that without it some commands don't update immediately
        await self.shash_handler.sync_all_commands()

    def get_command_resp(self, command: str, noinline: bool) -> tuple[Union[str, None], Union[Embed, None], list[File]]:
        command_info: dict = self.commands_list[command]

        # If the command is a copy of another command, run this function with the actual command
        if command_info.get('copy_of'):
            self.logger.debug('Command /{} is a copy of /{}, re-running function with that command'.format(
                command, command_info.get('copy_of')
            ))
            return self.get_command_resp(command_info.get('copy_of'), noinline)

        # If we have attachments for this command, read them out and collect them in a list
        files_to_attach: list[File] = []
        if os.path.isdir(os.path.join(attachments_dir, command)):
            for file_or_folder in os.listdir(os.path.join(attachments_dir, command)):
                if not os.path.isfile(os.path.join(os.path.join(attachments_dir, command), file_or_folder)):
                    continue
                files_to_attach.append(File(fp=os.path.join(os.path.join(attachments_dir, command), file_or_folder)))

        # If we don't have a main 'message' component, we don't have to do any formatting
        if not command_info.get('message'):
            return command_info.get('raw_message'), None, files_to_attach

        embed = Embed(description='', colour=embed_color)
        # If we don't have inline links, we don't have to look at 'noinline' at all
        if not command_info.get('has_inline', False):
            # We can only either have a string or a list of strings here. If we have just one string, set that as the
            # description. If we have multiple, join them together
            if type(command_info.get('message')) is str:
                embed_description = command_info.get('message')
            else:
                embed_description = ''.join(command_info.get('message'))
        # We have inline links
        else:
            if type(command_info.get('message')) is dict:
                if noinline:
                    embed_description = '{}: {}'
                else:
                    embed_description = '[{}]({})'
                embed_description = embed_description.format(
                    command_info.get('message').get('text'), command_info.get('message').get('link')
                )
            # We have a list of either text or links
            else:
                embed_description = ''
                message: list[Union[dict, str]] = command_info.get('message')
                for message_part in message:
                    if type(message_part) is str:
                        embed_description += message_part
                    # We have a link (dict) now
                    else:
                        if noinline:
                            part_to_add = '{}: {}'
                            # If we have a word right after the link, add a space before it
                            try:
                                next_message_part: str = message[message.index(message_part) + 1]
                            except IndexError:
                                pass
                            else:
                                if type(next_message_part) is str and next_message_part[0] not in (' ', '.', ','):
                                    part_to_add += ' '
                        else:
                            part_to_add = '[{}]({})'
                        embed_description += part_to_add.format(
                            message_part.get('text'), message_part.get('link')
                        )

        # If we have extra description for when inline links are disabled, add that to the description
        if noinline and command_info.get('noinline_add'):
            embed_description += '\n\n'
            embed_description += command_info.get('noinline_add')
        embed.description = embed_description
        return command_info.get('raw_message'), embed, files_to_attach

    async def handle_command(self, ctx: SlashContext, noinline: bool = None, mention: User = None):
        self.logger.info('{} used /{} in #{}'.format(ctx.author, ctx.command, ctx.channel))

        # If the channel name the command was used in contains "commands" and the user hasn't specifically turned on
        # inline links, assume they want inline links turned off
        if noinline is None:
            noinline = 'commands' in ctx.channel.name

        message, embed, attachments = self.get_command_resp(ctx.command, noinline)

        await ctx.defer()

        async with ctx.channel.typing():
            if mention:
                message = mention.mention + (f'\n{message}' if message else '')

            if message or embed:
                await ctx.send(content=message, embed=embed)

            # If we don't have attachments, we of course can't send any
            # If 'noinline' is set, the attachment links will already be in the original message
            # *unless* we don't have an original message, in which case we'll always have to send them
            if attachments and not (noinline and (message or embed)):
                # We can only send attachments if we either have access to the channel or we haven't replied to the
                # command yet
                can_send_attachments = ctx.channel or (not message and not embed)
                if can_send_attachments:
                    if not message and not embed:
                        await ctx.send(files=attachments)
                    else:
                        await ctx.channel.send(files=attachments)

    def is_interesting_message(self, msg: Message) -> bool:
        return msg.attachments and msg.author != self.user


def button_check(ctx: ComponentContext) -> bool:
    # Always allow button presses when in DMs/Groups
    if not ctx.guild:
        return True

    # If we are in a guild, check if the member is allowed to press the button
    member: Member = ctx.guild.get_member(ctx.author.id)
    if not member:
        return False
    return any(role.id in sysinfo_allowed_roles for role in member.roles)
