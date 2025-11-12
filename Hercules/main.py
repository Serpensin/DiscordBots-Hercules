#Import
import time
startupTime_start = time.time()
import aiohttp
import asyncio
import datetime
import discord
import hercules
import json
import jsonschema
import os
import platform
import psutil
import re
import sentry_sdk
import signal
import sys
import tempfile
from CustomModules import bot_directory
from CustomModules import log_handler
from dotenv import load_dotenv
from random import randrange
from typing import Optional, Any, Tuple
from urllib.parse import urlparse, unquote
from zipfile import ZIP_DEFLATED, ZipFile



#Init
discord.VoiceClient.warn_nacl = False
load_dotenv()
APP_FOLDER_NAME = 'Hercules-Bot'
BOT_NAME = 'Hercules'
os.makedirs(f'{APP_FOLDER_NAME}//Logs', exist_ok=True)
os.makedirs(f'{APP_FOLDER_NAME}//Buffer', exist_ok=True)
LOG_FOLDER = f'{APP_FOLDER_NAME}//Logs//'
BUFFER_FOLDER = f'{APP_FOLDER_NAME}//Buffer//'
ACTIVITY_FILE = f'{APP_FOLDER_NAME}//activity.json'
BOT_VERSION = "1.4.11"
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    environment='Production',
    release=f'{BOT_NAME}@{BOT_VERSION}'
)

#Load env
TOKEN = os.getenv('TOKEN')
OWNERID = os.getenv('OWNER_ID')
LOG_LEVEL = os.getenv('LOG_LEVEL')
SUPPORTID = os.getenv('SUPPORT_SERVER')
TOPGG_TOKEN = os.getenv('TOPGG_TOKEN')
DEBUG_CHANNEL_ID = int(os.getenv('DEBUG_CHANNEL', '1358836394398847155'))

#Logger init
log_manager = log_handler.LogManager(LOG_FOLDER, BOT_NAME, LOG_LEVEL)
discord_logger = log_manager.get_logger('discord')
program_logger = log_manager.get_logger('Program')
program_logger.info('Engine powering up...')

Hercules = hercules.Hercules(program_logger)

#Create activity.json if not exists
class JSONValidator:
    schema = {
        "type" : "object",
        "properties" : {
            "activity_type" : {
                "type" : "string",
                "enum" : ["Playing", "Streaming", "Listening", "Watching", "Competing"]
            },
            "activity_title" : {"type" : "string"},
            "activity_url" : {"type" : "string"},
            "status" : {
                "type" : "string",
                "enum" : ["online", "idle", "dnd", "invisible"]
            },
        },
    }

    default_content = {
        "activity_type": "Playing",
        "activity_title": "Made by Serpensin: https://serpensin.com/",
        "activity_url": "",
        "status": "online"
    }

    def __init__(self, file_path):
        self.file_path = file_path

    def validate_and_fix_json(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as file:
                try:
                    data = json.load(file)
                    jsonschema.validate(instance=data, schema=self.schema)  # validate the data
                except (jsonschema.exceptions.ValidationError, json.decoder.JSONDecodeError) as e:
                    program_logger.error(f'ValidationError: {e}')
                    self.write_default_content()
        else:
            self.write_default_content()

    def write_default_content(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.default_content, file, indent=4)
validator = JSONValidator(ACTIVITY_FILE)
validator.validate_and_fix_json()


class aclient(discord.AutoShardedClient):
    def __init__(self):

        intents = discord.Intents.default()
        #intents.guild_messages = True
        #intents.members = True

        super().__init__(owner_id = OWNERID,
                              intents = intents,
                              status = discord.Status.invisible,
                              auto_reconnect = True
                        )
        self.synced = False
        self.initialized = False


    class Presence():
        @staticmethod
        def get_activity() -> discord.Activity:
            with open(ACTIVITY_FILE) as f:
                data = json.load(f)
                activity_type = data['activity_type']
                activity_title = data['activity_title']
                activity_url = data['activity_url']
            if activity_type == 'Playing':
                return discord.Game(name=activity_title)
            elif activity_type == 'Streaming':
                return discord.Streaming(name=activity_title, url=activity_url)
            elif activity_type == 'Listening':
                return discord.Activity(type=discord.ActivityType.listening, name=activity_title)
            elif activity_type == 'Watching':
                return discord.Activity(type=discord.ActivityType.watching, name=activity_title)
            elif activity_type == 'Competing':
                return discord.Activity(type=discord.ActivityType.competing, name=activity_title)

        @staticmethod
        def get_status() -> discord.Status:
            with open(ACTIVITY_FILE) as f:
                data = json.load(f)
                status = data['status']
            if status == 'online':
                return discord.Status.online
            elif status == 'idle':
                return discord.Status.idle
            elif status == 'dnd':
                return discord.Status.dnd
            elif status == 'invisible':
                return discord.Status.invisible


    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
        options = interaction.data.get("options")
        option_values = ""
        if options:
            for option in options:
                option_values += f"{option['name']}: {option['value']}"
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(f'This command is on cooldown.\nTime left: `{str(datetime.timedelta(seconds=int(error.retry_after)))}`', ephemeral=True)
        else:
            try:
                try:
                    await interaction.response.send_message(f"Error! Try again.", ephemeral=True)
                except:
                    try:
                        await interaction.followup.send(f"Error! Try again.", ephemeral=True)
                    except:
                        pass
            except discord.Forbidden:
                try:
                    await interaction.followup.send(f"{error}\n\n{option_values}", ephemeral=True)
                except discord.NotFound:
                    try:
                        await interaction.response.send_message(f"{error}\n\n{option_values}", ephemeral=True)
                    except discord.NotFound:
                        pass
                except Exception as e:
                    discord_logger.warning(f"Unexpected error while sending message: {e}")
            finally:
                try:
                    program_logger.warning(f"{error} -> {option_values} | Invoked by {interaction.user.name} ({interaction.user.id}) @ {interaction.guild.name} ({interaction.guild.id}) with Language {interaction.locale[1]}")
                except AttributeError:
                    program_logger.warning(f"{error} -> {option_values} | Invoked by {interaction.user.name} ({interaction.user.id}) with Language {interaction.locale[1]}")
                sentry_sdk.capture_exception(error)

    async def on_guild_join(self, guild):
        if not self.synced:
            return
        discord_logger.info(f'I joined {guild}. (ID: {guild.id})')

    async def on_message(self, message):
        async def __wrong_selection():
            await message.channel.send('```'
                                       'Commands:\n'
                                       'help - Shows this message\n'
                                       'log - Get the log\n'
                                       'activity - Set the activity of the bot\n'
                                       'status - Set the status of the bot\n'
                                       'shutdown - Shutdown the bot\n'
                                       '```')

        if message.guild is None and message.author.id == int(OWNERID):
            args = message.content.split(' ')
            program_logger.debug(args)
            command, *args = args
            if command == 'help':
                await __wrong_selection()
                return
            elif command == 'log':
                await Owner.log(message, args)
                return
            elif command == 'activity':
                await Owner.activity(message, args)
                return
            elif command == 'status':
                await Owner.status(message, args)
                return
            elif command == 'shutdown':
                await Owner.shutdown(message)
                return
            else:
                await __wrong_selection()

    async def on_guild_remove(self, guild):
        if not self.synced:
            return
        program_logger.info(f'I got kicked from {guild}. (ID: {guild.id})')

    async def setup_hook(self):
        global owner, shutdown
        shutdown = False
        try:
            owner = await self.fetch_user(OWNERID)
            if owner is None:
                program_logger.critical(f"Invalid ownerID: {OWNERID}")
                sys.exit(f"Invalid ownerID: {OWNERID}")
        except discord.HTTPException as e:
            program_logger.critical(f"Error fetching owner user: {e}")
            sys.exit(f"Error fetching owner user: {e}")
        discord_logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
        discord_logger.info('Syncing...')
        await tree.sync()
        discord_logger.info('Synced.')
        self.synced = True
        self.stats = bot_directory.Stats(bot=bot,
                                    logger=program_logger,
                                    topgg_token=TOPGG_TOKEN,
                                    )

    async def on_ready(self):
        await bot.change_presence(activity = self.Presence.get_activity(), status = self.Presence.get_status())
        if self.initialized:
            return
        self.stats.start_stats_update()
        program_logger.info(r'''
                           _
  /\  /\___ _ __ ___ _   _| | ___  ___
 / /_/ / _ \ '__/ __| | | | |/ _ \/ __|
/ __  /  __/ | | (__| |_| | |  __/\__ \
\/ /_/ \___|_|  \___|\__,_|_|\___||___/
        ''')
        bot.loop.create_task(Tasks.health_server())
        global start_time
        start_time = datetime.datetime.now(datetime.UTC)
        program_logger.info(f"Initialization completed in {time.time() - startupTime_start} seconds.")
        self.initialized = True

bot = aclient()
tree = discord.app_commands.CommandTree(bot)
tree.on_error = bot.on_app_command_error


class SignalHandler:
    def __init__(self):
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        program_logger.info('Received signal to shutdown...')
        bot.loop.create_task(Owner.shutdown(owner))



#Fix error on windows on shutdown
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())



class Tasks():
    async def health_server():
        async def __health_check(request):
            return aiohttp.web.Response(text="Healthy")

        app = aiohttp.web.Application()
        app.router.add_get('/health', __health_check)
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', 5000)
        try:
            await site.start()
        except OSError as e:
            program_logger.warning(f'Error while starting health server: {e}')


#Functions
class Functions():
    async def get_or_fetch(item: str, item_id: int) -> Optional[Any]:
        """
        Attempts to retrieve an object using the 'get_<item>' method of the bot class, and
        if not found, attempts to retrieve it using the 'fetch_<item>' method.

        :param item: Name of the object to retrieve
        :param item_id: ID of the object to retrieve
        :return: Object if found, else None
        :raises AttributeError: If the required methods are not found in the bot class
        """
        get_method_name = f'get_{item}'
        fetch_method_name = f'fetch_{item}'

        get_method = getattr(bot, get_method_name, None)
        fetch_method = getattr(bot, fetch_method_name, None)

        if get_method is None or fetch_method is None:
            raise AttributeError(f"Methods {get_method_name} or {fetch_method_name} not found on bot object.")

        item_object = get_method(item_id)
        if item_object is None:
            try:
                item_object = await fetch_method(item_id)
            except discord.NotFound:
                pass
        return item_object

    async def is_valid_url_and_lua_syntax(url: str) -> Tuple[bool, str]:
        url = unquote(url)

        url_pattern = re.compile(
            r'^(https?):\/\/'
            r'([a-zA-Z0-9]+(:[a-zA-Z0-9]+)?@)?'
            r'(([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})'
            r'(:[0-9]{1,5})?'
            r'(\/[a-zA-Z0-9._\-\/]*)?$'
        )

        if not url_pattern.match(url):
            return False, "Invalid URL."

        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    if response.status not in [200, 204, 301, 302]:
                        return False, f"HTTP Error: {response.status}"
                    if int(response.headers.get('Content-Length', 0)) > 5 * 1024 * 1024:
                        return False, "File is too big. (Max: 5MB)"

                async with session.get(url) as response:
                    if response.status not in [200, 204, 301, 302]:
                        return False, f"HTTP Error: {response.status}"
                    lua_code = await response.text()
                    isValid, conout = Hercules.isValidLUASyntax(lua_code)
                    if isValid:
                        return True, lua_code
                    else:
                        return False, conout
        except aiohttp.ClientError as e:
            program_logger.error(f"Error fetching URL: {e}")
            return False, "URL not reachable."

    async def send_file(interaction: discord.Interaction, file_path: str):
        try:
            await interaction.followup.send(f"{interaction.user.mention}\nObfuscation complete!", file=discord.File(file_path), ephemeral=True)
        except discord.HTTPException as err:
            if err.status == 413:
                zip_file = f'{BUFFER_FOLDER}{interaction.user.id}_{randrange(0, 9999)}.zip'
                with ZipFile(zip_file, mode='w', compression=ZIP_DEFLATED, compresslevel=9, allowZip64=True) as f:
                    f.write(file_path)
                try:
                    await interaction.followup.send(f"{interaction.user.mention}\nObfuscation complete!", file=discord.File(zip_file), ephemeral=True)
                except discord.HTTPException as err:
                    if err.status == 413:
                        await interaction.followup.send(f"{interaction.user.mention}\nObfuscation complete! The file is too big to be sent directly.")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
            if 'zip_file' in locals() and os.path.exists(zip_file):
                os.remove(zip_file)

    async def create_support_invite(interaction):
        try:
            guild = bot.get_guild(int(SUPPORTID))
        except ValueError:
            return "Could not find support guild."
        if guild is None:
            return "Could not find support guild."
        if not guild.text_channels:
            return "Support guild has no text channels."
        try:
            member = await guild.fetch_member(interaction.user.id)
        except discord.NotFound:
            member = None
        if member is not None:
            return "You are already in the support guild."
        channels: discord.TextChannel = guild.text_channels
        for channel in channels:
            try:
                if interaction.guild is not None:
                    reason=f"Created invite for {interaction.user.name} from server {interaction.guild.name} ({interaction.guild_id})"
                else:
                    reason=f"Created invite for {interaction.user.name} (DM)"

                invite: discord.Invite = await channel.create_invite(
                    reason=reason,
                    max_age=60,
                    max_uses=1,
                    unique=True
                )

                return invite.url
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue
        return "Could not create invite. There is either no text-channel, or I don't have the rights to create an invite."

    async def send_debug_files(interaction: discord.Interaction, error_text: str, original_code: str) -> bool:
        temp_file_path = ''
        to_send = None
        file_url = os.path.abspath(f'{BUFFER_FOLDER}{interaction.user.id}_url.lua')
        file_file = os.path.abspath(f'{BUFFER_FOLDER}{interaction.user.id}_file.lua')

        if os.path.exists(file_url):
            to_send = file_url
        elif os.path.exists(file_file):
            to_send = file_file
        else:
            return False

        with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, encoding='utf-8', mode='w') as original_temp:
            original_temp.write(original_code)
            orig_file_path = original_temp.name

        channel: discord.TextChannel = await Functions.get_or_fetch('channel', DEBUG_CHANNEL_ID)

        try:
            if len(error_text) > 1900:
                with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, encoding='utf-8', mode='w') as temp_file:
                    temp_file.write(error_text)
                    temp_file_path = temp_file.name
                await channel.send(content=f"A error appeared during/after obfuscation, executed by {interaction.user.mention}.:\n", files=[discord.File(temp_file_path, filename='ErrorMessage.txt'), discord.File(orig_file_path, filename='Input.lua'), discord.File(to_send, filename='Output.lua')])
                return True
            else:
                await channel.send(content=f"A error appeared during/after obfuscation, executed by {interaction.user.mention}.:\n```txt\n{error_text}```", files=[discord.File(orig_file_path, filename='Input.lua'), discord.File(to_send, filename='Output.lua')])
                return True
        except discord.errors.DiscordException as e:
            program_logger.error(f'Error while sending debug files -> {e}')
            return False
        finally:
            os.remove(orig_file_path)
            os.remove(to_send)
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)


##Owner Commands
class Owner():
    async def log(message, args):
        async def __wrong_selection():
            await message.channel.send('```'
                                       'log [current/folder/lines] (Replace lines with a positive number, if you only want lines.) - Get the log\n'
                                       '```')
        if not args:
            await __wrong_selection()
            return

        command = args[0]
        if command == 'current':
            log_file_path = f'{LOG_FOLDER}{BOT_NAME}.log'
            try:
                await message.channel.send(file=discord.File(log_file_path))
            except discord.HTTPException as err:
                if err.status == 413:
                    zip_path = f'{BUFFER_FOLDER}Logs.zip'
                    with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED, compresslevel=9, allowZip64=True) as zip_file:
                        zip_file.write(log_file_path)
                    try:
                        await message.channel.send(file=discord.File(zip_path))
                    except discord.HTTPException as err:
                        if err.status == 413:
                            await message.channel.send("The log is too big to be sent directly.\nYou have to look at the log in your server (VPS).")
                    os.remove(zip_path)
            return

        if command == 'folder':
            zip_path = f'{BUFFER_FOLDER}Logs.zip'
            if os.path.exists(zip_path):
                os.remove(zip_path)
            with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED, compresslevel=9, allowZip64=True) as zip_file:
                for file in os.listdir(LOG_FOLDER):
                    if not file.endswith(".zip"):
                        zip_file.write(f'{LOG_FOLDER}{file}')
            try:
                await message.channel.send(file=discord.File(zip_path))
            except discord.HTTPException as err:
                if err.status == 413:
                    await message.channel.send("The folder is too big to be sent directly.\nPlease get the current file or the last X lines.")
            os.remove(zip_path)
            return

        try:
            lines = int(command)
            if lines < 1:
                await __wrong_selection()
                return
        except ValueError:
            await __wrong_selection()
            return

        log_file_path = f'{LOG_FOLDER}{BOT_NAME}.log'
        buffer_file_path = f'{BUFFER_FOLDER}log-lines.txt'
        with open(log_file_path, 'r', encoding='utf8') as log_file:
            log_lines = log_file.readlines()[-lines:]
        with open(buffer_file_path, 'w', encoding='utf8') as buffer_file:
            buffer_file.writelines(log_lines)
        await message.channel.send(content=f'Here are the last {len(log_lines)} lines of the current logfile:', file=discord.File(buffer_file_path))
        os.remove(buffer_file_path)

    async def activity(message, args):
        async def __wrong_selection():
            await message.channel.send('```'
                                       'activity [playing/streaming/listening/watching/competing] [title] (url) - Set the activity of the bot\n'
                                       '```')
        def isURL(zeichenkette):
            try:
                ergebnis = urlparse(zeichenkette)
                return all([ergebnis.scheme, ergebnis.netloc])
            except:
                return False

        def remove_and_save(liste):
            if liste and isURL(liste[-1]):
                return liste.pop()
            else:
                return None

        if args == []:
            await __wrong_selection()
            return
        action = args[0].lower()
        url = remove_and_save(args[1:])
        title = ' '.join(args[1:])
        program_logger.debug(title)
        program_logger.debug(url)
        with open(ACTIVITY_FILE, 'r', encoding='utf8') as f:
            data = json.load(f)
        if action == 'playing':
            data['activity_type'] = 'Playing'
            data['activity_title'] = title
            data['activity_url'] = ''
        elif action == 'streaming':
            data['activity_type'] = 'Streaming'
            data['activity_title'] = title
            data['activity_url'] = url
        elif action == 'listening':
            data['activity_type'] = 'Listening'
            data['activity_title'] = title
            data['activity_url'] = ''
        elif action == 'watching':
            data['activity_type'] = 'Watching'
            data['activity_title'] = title
            data['activity_url'] = ''
        elif action == 'competing':
            data['activity_type'] = 'Competing'
            data['activity_title'] = title
            data['activity_url'] = ''
        else:
            await __wrong_selection()
            return
        with open(ACTIVITY_FILE, 'w', encoding='utf8') as f:
            json.dump(data, f, indent=2)
        await bot.change_presence(activity = bot.Presence.get_activity(), status = bot.Presence.get_status())
        await message.channel.send(f'Activity set to {action} {title}{" " + url if url else ""}.')

    async def status(message, args):
        async def __wrong_selection():
            await message.channel.send('```'
                                       'status [online/idle/dnd/invisible] - Set the status of the bot\n'
                                       '```')

        if args == []:
            await __wrong_selection()
            return
        action = args[0].lower()
        with open(ACTIVITY_FILE, 'r', encoding='utf8') as f:
            data = json.load(f)
        if action == 'online':
            data['status'] = 'online'
        elif action == 'idle':
            data['status'] = 'idle'
        elif action == 'dnd':
            data['status'] = 'dnd'
        elif action == 'invisible':
            data['status'] = 'invisible'
        else:
            await __wrong_selection()
            return
        with open(ACTIVITY_FILE, 'w', encoding='utf8') as f:
            json.dump(data, f, indent=2)
        await bot.change_presence(activity = bot.Presence.get_activity(), status = bot.Presence.get_status())
        await message.channel.send(f'Status set to {action}.')

    async def shutdown(message):
        global shutdown
        _message = 'Engine powering down...'
        program_logger.info(_message)
        try:
            await message.channel.send(_message)
        except:
            await owner.send(_message)
        await bot.change_presence(status=discord.Status.invisible)
        shutdown = True

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

        bot.stats.stop_stats_update()

        await bot.close()



##Bot Commands
#Ping
@tree.command(name = 'ping', description = 'Test, if the bot is responding.')
@discord.app_commands.checks.cooldown(1, 30, key=lambda i: (i.user.id))
async def cmd_ping(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    before = time.monotonic()
    await interaction.followup.send('Pong!')
    ping = (time.monotonic() - before) * 1000
    gateway_ping = bot.latency * 1000 if interaction.guild is None else bot.shards.get(interaction.guild.shard_id).latency * 1000
    await interaction.edit_original_response(content=f'Pong! \nCommand execution time: `{ping:.2f}ms`\nPing to gateway: `{gateway_ping:.2f}ms`')


#Bot Info
@tree.command(name = 'botinfo', description = 'Get information about the bot.')
@discord.app_commands.checks.cooldown(1, 60, key=lambda i: (i.user.id))
async def cmd_botinfo(interaction: discord.Interaction):
    member_count = sum(guild.member_count for guild in bot.guilds)

    embed = discord.Embed(
        title=f"Information about {bot.user.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else '')

    embed.add_field(name="Created at", value=bot.user.created_at.strftime("%d.%m.%Y, %H:%M:%S"), inline=True)
    embed.add_field(name="Bot-Version", value=BOT_VERSION, inline=True)
    embed.add_field(name="Uptime", value=str(datetime.timedelta(seconds=int((datetime.datetime.now(datetime.UTC) - start_time).total_seconds()))), inline=True)

    embed.add_field(name="Bot-Owner", value=f"<@!{OWNERID}>", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    embed.add_field(name="Server", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Member count", value=str(member_count), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    embed.add_field(name="Shards", value=f"{bot.shard_count}", inline=True)
    embed.add_field(name="Shard ID", value=f"{interaction.guild.shard_id if interaction.guild else 'N/A'}", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    embed.add_field(name="Python-Version", value=f"{platform.python_version()}", inline=True)
    embed.add_field(name="discord.py-Version", value=f"{discord.__version__}", inline=True)
    embed.add_field(name="Sentry-Version", value=f"{sentry_sdk.consts.VERSION}", inline=True)

    embed.add_field(name="Repo", value=f"[GitHub](https://github.com/Serpensin/DiscordBots-Hercules)", inline=True)
    embed.add_field(name="Invite", value=f"[Invite me](https://discord.com/oauth2/authorize?client_id={bot.user.id})", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    if interaction.user.id == int(OWNERID):
        # Add CPU and RAM usage
        process = psutil.Process(os.getpid())
        cpu_usage = process.cpu_percent()
        ram_usage = round(process.memory_percent(), 2)
        ram_real = round(process.memory_info().rss / (1024 ** 2), 2)

        embed.add_field(name="CPU", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="RAM", value=f"{ram_usage}%", inline=True)
        embed.add_field(name="RAM", value=f"{ram_real} MB", inline=True)

    await interaction.response.send_message(embed=embed)


#Help
@tree.command(name = 'help', description = 'Explains how to use this obfuscator.')
@discord.app_commands.checks.cooldown(1, 30, key=lambda i: (i.user.id))
async def cmd_help(interaction: discord.Interaction):
    commands_help = (
        "**/obfuscate_url [url]**:\nSubmit a URL (e.g. from pastebin) containing a Lua file. Hercules will process and obfuscate it.\n\n"
        "**/obfuscate_file [file]**:\nUpload a `.lua` file along with this command. Hercules will add it to the queue and notify you once it's done.\n\n"
        "**/check_url [url]**:\nCheck if a URL (e.g. from pastebin) contains valid Lua syntax.\n\n"
        "**/check_file [file]**:\nUpload a `.lua` file along with this command to check if it contains valid Lua syntax.\n\n\n"
    )

    methods_explanations = "**Obfuscation Methods:**\n\n"
    for method in Hercules.methods:
        methods_explanations += f"**{method['name']}**:\n{method['explanation']}\n\n"

    embed = discord.Embed(
        title="Hercules Bot - Help",
        description=commands_help + methods_explanations,
        color=discord.Color.blue()
    )

    embed.set_footer(text="Happy obfuscating! 🛡️")
    await interaction.response.send_message(embed=embed)


#Support Invite
@tree.command(name = 'support', description = 'Get invite to our support server.')
@discord.app_commands.checks.cooldown(1, 60, key=lambda i: (i.user.id))
async def cmd_support(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    if not SUPPORTID:
        await interaction.followup.send('There is no support server setup!', ephemeral=True)
        return
    if interaction.guild is None:
        await interaction.followup.send(await Functions.create_support_invite(interaction), ephemeral=True)
        return
    if str(interaction.guild.id) != SUPPORTID:
        await interaction.followup.send(await Functions.create_support_invite(interaction), ephemeral=True)
    else:
        await interaction.followup.send('You are already in our support server!', ephemeral=True)




##Obfucation Commands
#View
class ModeSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.selected_bits = sum((1 << method['bitkey']) for method in Hercules.methods if method['enabled'])
        self.timedout = False
        self.buttons_per_row = 5
        self.create_buttons()

    def toggle_bit(self, bit_position):
        self.selected_bits ^= (1 << bit_position)

    def create_buttons(self):
        for idx, method in enumerate(Hercules.methods):
            method_name = method['name']
            bit_position = method['bitkey']
            is_selected = self.selected_bits & (1 << bit_position) != 0
            row = (idx // self.buttons_per_row) + 1

            button = self.MethodButton(
                label=method_name,
                bit_position=bit_position,
                selected=is_selected,
                disabled=not method['enabled']
            )
            button.row = row
            self.add_item(button)

    class MethodButton(discord.ui.Button):
        def __init__(self, label, bit_position, selected=False, disabled=False):
            super().__init__(
                label=label + (' (Selected)' if selected else ''),
                style=discord.ButtonStyle.success if selected else discord.ButtonStyle.primary,
                row=None,
                disabled=disabled
            )
            self.bit_position = bit_position

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            if view.selected_bits & (1 << self.bit_position):
                view.toggle_bit(self.bit_position)
                self.label = self.label.replace(' (Selected)', '')
                self.style = discord.ButtonStyle.primary
            else:
                view.toggle_bit(self.bit_position)
                self.label += ' (Selected)'
                self.style = discord.ButtonStyle.success

            await interaction.response.edit_message(view=view)

    @discord.ui.button(label='Submit', style=discord.ButtonStyle.danger, row=0)
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_bits == 0:
            await interaction.response.send_message("You must select at least one obfuscation method!", ephemeral=True)
        else:
            await interaction.response.edit_message(view=None)
            self.stop()


class AskSendDebug(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=20)
        self.message: discord.Message = None
        self.error_text: str = None
        self.original_code: str
        self.answered = False

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.success)
    async def send_files_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.answered = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(content='Sending...', view=self)

        success = await Functions.send_debug_files(interaction, error_text=self.error_text, original_code=self.original_code)

        if success:
            await interaction.edit_original_response(content="Debug files sent successfully.", view=self)
        else:
            await interaction.edit_original_response(content="Debug files couldn't be sent!", view=self)

    @discord.ui.button(label='No', style=discord.ButtonStyle.danger)
    async def abort_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.answered = True
        await self.no(interaction)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message and not self.answered:
            await self.message.edit(content="Timeout: Debug files were not sent!", view=self)

    async def no(self, interaction: discord.Interaction):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(content="Debug files were not sent!", view=self)


#Fetch file from URL
@tree.command(name = 'obfuscate_url', description = 'Submit a URL containing a Lua file.')
# @discord.app_commands.checks.cooldown(1, 60, key=lambda i: (i.user.id))
@discord.app_commands.describe(url = 'The URL of the Lua file.',
                               optional_preset = 'Optional presets that can be used.'
                               )
@discord.app_commands.choices(
    optional_preset = [
        discord.app_commands.Choice(name='Minimal parameters for lighter obfuscation.', value='min'),
        discord.app_commands.Choice(name='Moderate parameters for balanced obfuscation.', value='mid'),
        discord.app_commands.Choice(name='Maximum parameters for heavier obfuscation.', value='max')
        ]
    )
async def cmd_obfuscate_url(interaction: discord.Interaction,
               url: str,
               optional_preset: str = None
               ):
    await interaction.response.defer(ephemeral=True)
    valid, conout = await Functions.is_valid_url_and_lua_syntax(url)
    if not valid:
        # Check if output exceeds Discord's character limit (adding some margin for the message text and markdown)
        if len(conout) > 1900:
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, encoding='utf-8', mode='w') as temp_file:
                temp_file.write(conout)
                temp_file_path = temp_file.name
            await interaction.edit_original_response(content="The URL is not reachable or does not contain valid Lua syntax.")
            await interaction.followup.send(content="Details:", file=discord.File(temp_file_path, filename='error_output.txt'), ephemeral=True)
            os.remove(temp_file_path)
        else:
            await interaction.edit_original_response(content=f"The URL is not reachable or does not contain valid Lua syntax.:\n```txt\n{conout}```")
        return
    else:
        original_code = conout
        view = ModeSelectionView()

        await interaction.edit_original_response(content=f"Please select the obfuscation methods you want to use for {url}.", view=view)

        await view.wait()
        selected_bits = view.selected_bits

        file_path = os.path.abspath(f'{BUFFER_FOLDER}{interaction.user.id}_url.lua')
        with open(file_path, 'w', encoding='utf8') as f:
            f.write(conout)

        success, conout = Hercules.obfuscate(file_path, selected_bits, optional_preset)
        if not success:
            view = AskSendDebug()

            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, encoding='utf-8', mode='w') as temp_file:
                temp_file.write(conout)
                temp_file_path = temp_file.name

            message = await interaction.followup.send(f"{interaction.user.mention}\nObfuscation failed. Please try again.\nSend the original file to the owner for debug?", file=discord.File(temp_file_path, filename='Error.txt'), view=view, ephemeral=True)
            await interaction.delete_original_response()
            view.message = message
            view.error_text = conout
            view.original_code = original_code
            await view.wait()
            os.remove(temp_file_path)
        else:
            await Functions.send_file(interaction, file_path)


#Fetch file from upload
@tree.command(name = 'obfuscate_file', description = 'Upload a Lua file.')
# @discord.app_commands.checks.cooldown(1, 60, key=lambda i: (i.user.id))
@discord.app_commands.describe(file = 'File to be obfuscated.',
                               optional_preset = 'Optional presets that can be used.'
                               )
@discord.app_commands.choices(
    optional_preset = [
        discord.app_commands.Choice(name='Minimal parameters for lighter obfuscation.', value='min'),
        discord.app_commands.Choice(name='Moderate parameters for balanced obfuscation.', value='mid'),
        discord.app_commands.Choice(name='Maximum parameters for heavier obfuscation.', value='max')
        ]
    )
async def cmd_obfuscate_file(interaction: discord.Interaction,
             file: discord.Attachment,
   optional_preset: str = None
            ):
    await interaction.response.defer(ephemeral=True)
    if not file.filename.endswith('.lua'):
        await interaction.edit_original_response(content="Please upload a `.lua` file.")
        return
    if file.size > 1024 * 1024 * 5:
        await interaction.edit_original_response(content="The file is too big. Please upload a file smaller than 5 MB.")
        return

    file_path = os.path.abspath(f'{BUFFER_FOLDER}{interaction.user.id}_file.lua')
    with open(file_path, 'wb') as f:
        f.write(await file.read())

    def detect_bom_encoding(file_path):
        with open(file_path, 'rb') as f:
            raw = f.read(4)
        if raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        elif raw.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        elif raw.startswith(b'\xfe\xff'):
            return 'utf-16-be'
        elif raw.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-32-le'
        elif raw.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32-be'
        return None

    encoding = detect_bom_encoding(file_path)
    if encoding:
        with open(file_path, 'r', encoding=encoding) as f:
            lua_code = f.read()
        with open(file_path, 'w', encoding='utf8') as f:
            f.write(lua_code)
    else:
        try:
            with open(file_path, 'r', encoding='utf8') as f:
                lua_code = f.read()
        except UnicodeDecodeError:
            for fallback_encoding in ['cp1252', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=fallback_encoding) as f:
                        lua_code = f.read()
                    with open(file_path, 'w', encoding='utf8') as f:
                        f.write(lua_code)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                with open(file_path, 'rb') as f:
                    raw = f.read()
                lua_code = raw.decode('utf-8', errors='replace')
                with open(file_path, 'w', encoding='utf8') as f:
                    f.write(lua_code)

    isValid, conout = Hercules.isValidLUASyntax(lua_code)
    if not isValid:
        # Check if output exceeds Discord's character limit (adding some margin for the message text and markdown)
        if len(conout) > 1900:
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, encoding='utf-8', mode='w') as temp_file:
                temp_file.write(conout)
                temp_file_path = temp_file.name
            await interaction.edit_original_response(content="The uploaded file does not contain valid Lua syntax.")
            await interaction.followup.send(content="Luacheck output:", file=discord.File(temp_file_path, filename='luacheck_output.txt'), ephemeral=True)
            os.remove(temp_file_path)
        else:
            await interaction.edit_original_response(content=f"The uploaded file does not contain valid Lua syntax.:\n```txt\n{conout}```")
        os.remove(file_path)
    else:
        view = ModeSelectionView()
        await interaction.edit_original_response(content=f"Please select the obfuscation methods you want to use for {file.filename}.", view=view)
        await view.wait()

        selected_bits = view.selected_bits

        success, conout = Hercules.obfuscate(file_path, selected_bits, optional_preset)
        if not success:
            view = AskSendDebug()

            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, encoding='utf-8', mode='w') as temp_file:
                temp_file.write(conout)
                temp_file_path = temp_file.name

            message = await interaction.followup.send(f"{interaction.user.mention}\nObfuscation failed. Please try again.\nSend the original file to the owner for debug?", file=discord.File(temp_file_path, filename='Error.txt'), view=view, ephemeral=True)
            await interaction.delete_original_response()
            view.message = message
            view.error_text = conout
            view.original_code = lua_code
            await view.wait()
            os.remove(temp_file_path)
        else:
            await Functions.send_file(interaction, file_path)


#Errorcheck from url
@tree.command(name = 'check_url', description = 'Check if the URL is reachable and contains valid Lua syntax.')
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: (i.user.id))
@discord.app_commands.describe(url = 'The URL to check.')
async def cmd_check_url(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=True)
    valid, conout = await Functions.is_valid_url_and_lua_syntax(url)
    if not valid:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, encoding='utf-8', mode='w') as temp_file:
            temp_file.write(conout)
            temp_file_path = temp_file.name
        await interaction.followup.send(content=f"The URL is not reachable or does not contain valid Lua syntax.", file=discord.File(temp_file_path))
        os.remove(temp_file_path)
    else:
        await interaction.followup.send(content="The URL is reachable and contains valid Lua syntax.")


#Error check from file
@tree.command(name = 'check_file', description = 'Check if the uploaded file contains valid Lua syntax.')
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: (i.user.id))
@discord.app_commands.describe(file = 'The file to check.')
async def cmd_check_file(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    if not file.filename.endswith('.lua'):
        await interaction.edit_original_response(content="Please upload a `.lua` file.")
        return
    if file.size > 1024 * 1024 * 5:
        await interaction.edit_original_response(content="The file is too big. Please upload a file smaller than 5 MB.")
        return

    file_path = os.path.abspath(f'{BUFFER_FOLDER}{interaction.user.id}_file.lua')
    with open(file_path, 'wb') as f:
        f.write(await file.read())

    with open(file_path, 'r', encoding='utf8') as f:
        lua_code = f.read()

    isValid, conout = Hercules.isValidLUASyntax(lua_code)
    if not isValid:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, encoding='utf-8', mode='w') as temp_file:
            temp_file.write(conout)
            temp_file_path = temp_file.name
        await interaction.followup.send(content=f"The uploaded file does not contain valid Lua syntax.", file=discord.File(temp_file_path))
        os.remove(temp_file_path)
    else:
        await interaction.followup.send(content="The uploaded file contains valid Lua syntax.")
    os.remove(file_path)




if __name__ == '__main__':
    if sys.version_info < (3, 11):
        program_logger.critical('Python 3.11 or higher is required.')
        sys.exit(1)
    if not TOKEN:
        program_logger.critical('Missing token. Please check your .env file.')
        sys.exit()
    else:
        SignalHandler()
        try:
            bot.run(TOKEN, log_handler=None)
        except discord.errors.LoginFailure:
            program_logger.critical('Invalid token. Please check your .env file.')
            sys.exit()
        except asyncio.CancelledError:
            if shutdown:
                pass
