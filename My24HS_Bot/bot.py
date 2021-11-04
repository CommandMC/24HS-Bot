import asyncio
import discord
import discord_slash
import logging
import os
import traceback
import yaml
from discord import File, Message, Member, Guild, Embed, Activity, ActivityType
from discord.ext.commands import Bot, Context
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from discord_slash.utils.manage_commands import create_option
from io import BytesIO, StringIO

from My24HS_Bot.const import commands_dir, sysinfo_allowed_roles, embed_color, attachments_dir
from My24HS_Bot.util import handle_sysinfo, is_sysinfo, convert_utf16_utf8


# Python doesn't allow classes to start with a number, so we have to add a "My" to the start of this
class My24HSbot(Bot):
    def __init__(self, **options):
        super().__init__(**options)
        self.shash_handler = discord_slash.SlashCommand(self)
        self.logger = logging.getLogger('24HS-Bot')
        self.commands_list: dict = {}
        self.is_started = False

    async def on_ready(self):
        # on_ready is called when the bot starts and when it reconnects. Thus, we can't just add the commands
        # every time we're in here, since that will error out with duplicate command warnings
        if self.is_started:
            return
        # Add and sync slash commands
        await self.sync_commands()
        # Add discord_components to the bot (to be able to use Buttons)
        DiscordComponents(self)
        await self.change_presence(activity=Activity(name='DanielIsCool.txt', type=ActivityType.watching))
        self.logger.info('on_ready finished, logged in as {}'.format(self.user))
        self.is_started = True

    async def on_guild_join(self, guild: Guild):
        self.logger.info('Joined a guild! {}'.format(guild.name))
        await self.sync_commands()

    async def on_guild_remove(self, guild: Guild):
        self.logger.info('Left a guild! {}'.format(guild.name))
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
            if fileext != '.yml':
                continue

            with open(os.path.join(commands_dir, file_or_folder)) as f:
                self.commands_list[filename] = yaml.safe_load(f)

        for command_name, command_info in self.commands_list.items():
            if command_info.get('copy_of'):
                self.logger.debug('Command {} is a copy of {}'.format(command_name, command_info.get('copy_of')))
                command_info = self.commands_list[command_info.get('copy_of')]

            # If the description is empty or not a string, we can't add the command
            if not command_info.get('description') or type(command_info.get('description')) is not str:
                self.logger.error('Cannot add command /{}, no description'.format(command_name))
                continue

            self.shash_handler.add_slash_command(
                cmd=self.handle_command,
                name=command_name,
                description=command_info.get('description'),
                guild_ids=list(guild.id for guild in self.guilds),
                options=[
                    create_option(
                        name='noinline',
                        description='Disable inline links in message',
                        option_type=5,
                        required=False
                    )
                ]
            )
        # Once all commands are added, push them to Discord
        # This might not be necessary anymore, but I've found that without it some commands don't update immediately
        await self.shash_handler.sync_all_commands()

    def get_command_resp(self, command: str, noinline: bool) -> tuple[(str, None), (Embed, None), list[File]]:
        if command not in self.commands_list:
            self.logger.error('Command /{} does not exist. This should be impossible!'.format(command))
            return None, Embed(), []

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
        else:
            # This shouldn't happen (since if we only have a string, the command can't have inline links since those
            # are dicts), but we'll handle it anyways
            if type(command_info.get('message')) is str:
                embed_description = command_info.get('message')
            # If we only have one embed link as the message, set that
            elif type(command_info.get('message')) is dict:
                if noinline:
                    embed_description = '{}: {}'
                else:
                    embed_description = '[{}]({})'
                embed_description = embed_description.format(
                    command_info.get('message').get('text'), command_info.get('message').get('link')
                )
            else:
                embed_description = ''
                message: list[(dict, str)] = command_info.get('message')
                for message_part in message:
                    if type(message_part) is str:
                        embed_description += message_part
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

    async def handle_command(self, ctx: Context, noinline: (bool, None) = None):
        self.logger.info('{} used /{} in #{}'.format(ctx.author, ctx.command, ctx.channel))
        # If the channel name the command was used in contains "commands" and the user hasn't specifically turned on
        # inline links, assume they want inline links turned off
        if noinline is None:
            noinline = 'commands' in ctx.channel.name
        message, embed, attachments = self.get_command_resp(ctx.command, noinline)
        # If we have neither a message nor an embed, only send the attachments (if any)
        if not message and not embed:
            if attachments:
                await ctx.send(
                    files=attachments
                )
            else:
                await ctx.send(
                    content='There was an error processing this command.'
                )
            return
        await ctx.send(
            content=message,
            embed=embed
        )
        # Send the attachments as a separate message, since otherwise they get displayed above the embed and that
        # looks weird
        if attachments:
            await ctx.channel.send(
                files=attachments
            )


def button_check(ctx, msg: Message) -> bool:
    # So, this gets ran whenever any button gets pressed. This creates an issue when two functions are waiting for a
    # button press at the same time, since both receive the same event, but only one should of course be triggered.
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
