import platform
from datetime import datetime
from base64 import b64decode
from asyncio import create_subprocess_exec, gather
from os import execl as osexecl
from signal import SIGINT, signal
from sys import executable
from time import time, monotonic
from uuid import uuid4
from requests import get as rget
from pytz import timezone
from bs4 import BeautifulSoup
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove as aioremove
from psutil import (boot_time, cpu_count, cpu_percent, cpu_freq, disk_usage, net_io_counters, swap_memory, virtual_memory)
from pyrogram.filters import command, private, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import (DATABASE_URL, INCOMPLETE_TASK_NOTIFIER, LOGGER, STOP_DUPLICATE_TASKS, Interval, QbInterval, bot, botStartTime, config_dict, scheduler, user_data, get_version)
from bot.helper.listeners.aria2_listener import start_aria2_listener

from .helper.ext_utils.bot_utils import (cmd_exec, get_readable_file_size, get_readable_time, new_thread, set_commands, sync_to_async, get_progress_bar_string, update_user_ldata)
from .helper.ext_utils.db_handler import DbManger
from .helper.ext_utils.fs_utils import clean_all, exit_clean_up, start_cleanup
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.telegram_helper.message_utils import (editMessage, sendFile, sendMessage, auto_delete_message)
from .modules import (anonymous, authorize, bot_settings, cancel_mirror, category_select, clone, eval, gd_count, gd_delete, gd_list, leech_del, mirror_leech, rmdb, rss, shell, status, torrent_search, torrent_select, users_settings, ytdlp, speedtest, save_msg, images, imdb, anilist, mediainfo, mydramalist, gen_pyro_sess, gd_clean, broadcast )
from .helper.themes import BotTheme


@new_thread
async def stats(_, message):
    if await aiopath.exists('.git'):
        last_commit = (await cmd_exec("git log -1 --date=short --pretty=format:'%cr'", True))[0]
        version = (await cmd_exec("git describe --abbrev=0 --tags", True))[0]
        change_log = (await cmd_exec("git log -1 --pretty=format:'%s'", True))[0]
    else:
        last_commit = 'No UPSTREAM_REPO'
        version = 'N/A'
        change_log = 'N/A'
    total, used, free, disk = disk_usage('/')
    swap = swap_memory()
    memory = virtual_memory()
    cpuUsage = cpu_percent(interval=0.5)


    DIR = 'Unlimited' if config_dict['DIRECT_LIMIT'] == '' else config_dict['DIRECT_LIMIT']
    YTD = 'Unlimited' if config_dict['YTDLP_LIMIT'] == '' else config_dict['YTDLP_LIMIT']
    GDL = 'Unlimited' if config_dict['GDRIVE_LIMIT'] == '' else config_dict['GDRIVE_LIMIT']
    TOR = 'Unlimited' if config_dict['TORRENT_LIMIT'] == '' else config_dict['TORRENT_LIMIT']
    CLL = 'Unlimited' if config_dict['CLONE_LIMIT'] == '' else config_dict['CLONE_LIMIT']
    MGA = 'Unlimited' if config_dict['MEGA_LIMIT'] == '' else config_dict['MEGA_LIMIT']
    TGL = 'Unlimited' if config_dict['LEECH_LIMIT'] == '' else config_dict['LEECH_LIMIT']
    UMT = 'Unlimited' if config_dict['USER_MAX_TASKS'] == '' else config_dict['USER_MAX_TASKS']
    BMT = 'Unlimited' if config_dict['QUEUE_ALL'] == '' else config_dict['QUEUE_ALL']

    stats = BotTheme('STATS',
                     last_commit=last_commit,
                     bot_version=get_version(),
                     commit_details=changelog,
                     bot_uptime=get_readable_time(time() - botStartTime),
                     os_uptime=get_readable_time(time() - boot_time()),
                     os_arch=f"{platform.system()}, {platform.release()}, {platform.machine()}",
                     cpu=cpuUsage,
                     cpu_bar=get_progress_bar_string(cpuUsage),
                     cpu_freq=f"{cpu_freq(percpu=False).current / 1000:.2f} GHz" if cpu_freq() else "Access Denied",
                     p_core=cpu_count(logical=False),
                     v_core=cpu_count(logical=True) - cpu_count(logical=False),
                     total_core=cpu_count(logical=True),
                     ram_bar=get_progress_bar_string(memory.percent),
                     ram=memory.percent,
                     ram_u=get_readable_file_size(memory.used),
                     ram_f=get_readable_file_size(memory.available),
                     ram_t=get_readable_file_size(memory.total),
                     swap_bar=get_progress_bar_string(swap.percent),
                     swap=swap.percent,
                     swap_u=get_readable_file_size(swap.used),
                     swap_f=get_readable_file_size(swap.free),
                     swap_t=get_readable_file_size(swap.total),
                     disk=disk,
                     disk_bar=get_progress_bar_string(disk),
                     disk_t=get_readable_file_size(total),
                     disk_u=get_readable_file_size(used),
                     disk_f=get_readable_file_size(free),
                     up_data=get_readable_file_size(
                         net_io_counters().bytes_sent),
                     dl_data=get_readable_file_size(
                         net_io_counters().bytes_recv)
                     )
    await sendMessage(message, stats, photo='IMAGES')
    await auto_delete_message(message, reply_message)


async def start(_, message):
    buttons = ButtonMaker()
    buttons.ubutton(BotTheme('ST_BN1_NAME'), BotTheme('ST_BN1_URL'))
    buttons.ubutton(BotTheme('ST_BN2_NAME'), BotTheme('ST_BN2_URL'))
    reply_markup = buttons.build_menu(2)
    if len(message.command) > 1 and message.command[1] == "wzmlx":
        await message.delete()
    elif len(message.command) > 1 and config_dict['TOKEN_TIMEOUT']:
        userid = message.from_user.id
        encrypted_url = message.command[1]
        input_token, pre_uid = (b64decode(encrypted_url.encode()).decode()).split('&&')
        if int(pre_uid) != userid:
            return await sendMessage(message, '<b>Temporary Token is not yours!</b>\n\n<i>Kindly generate your own.</i>')
        data = user_data.get(userid, {})
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, '<b>Temporary Token already used!</b>\n\n<i>Kindly generate a new one.</i>')
        elif config_dict['LOGIN_PASS'] is not None and data['token'] == config_dict['LOGIN_PASS']:
            return await sendMessage(message, '<b>Bot Already Logged In via Password</b>\n\n<i>No Need to Accept Temp Tokens.</i>')
        buttons.ibutton('Activate Temporary Token', f'pass {input_token}', 'header')
        reply_markup = buttons.build_menu(2)
        msg = '<b><u>Generated Temporary Login Token!</u></b>\n\n'
        msg += f'<b>Temp Token:</b> <code>{input_token}</code>\n\n'
        msg += f'<b>Validity:</b> {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]))}'
        return await sendMessage(message, msg, reply_markup)
    elif await CustomFilters.authorized(client, message):
        start_string = BotTheme('ST_MSG', help_command=f"/{BotCommands.HelpCommand}")
        await sendMessage(message, start_string, reply_markup, photo='IMAGES')
    elif config_dict['DM_MODE']:
        await sendMessage(message, BotTheme('ST_BOTPM'), reply_markup, photo='IMAGES')
    else:
        await sendMessage(message, BotTheme('ST_UNAUTH'), reply_markup, photo='IMAGES')
    await DbManger().update_pm_users(message.from_user.id)

async def token_callback(_, query):
    user_id = query.from_user.id
    input_token = query.data.split()[1]
    data = user_data.get(user_id, {})
    if 'token' not in data or data['token'] != input_token:
        return await query.answer('Already Used, Generate New One', show_alert=True)
    update_user_ldata(user_id, 'token', str(uuid4()))
    update_user_ldata(user_id, 'time', time())
    await query.answer('Activated Temporary Token!', show_alert=True)
    kb = query.message.reply_markup.inline_keyboard[1:]
    kb.insert(0, [InlineKeyboardButton('✅️ Activated ✅', callback_data='pass activated')])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(kb))


async def login(_, message):
    if config_dict['LOGIN_PASS'] is None:
        return
    elif len(message.command) > 1:
        user_id = message.from_user.id
        input_pass = message.command[1]
        if user_data.get(user_id, {}).get('token', '') == config_dict['LOGIN_PASS']:
            return await sendMessage(message, '<b>Already Bot Login In!</b>')
        if input_pass == config_dict['LOGIN_PASS']:
            update_user_ldata(user_id, 'token', config_dict['LOGIN_PASS'])
            return await sendMessage(message, '<b>Bot Permanent Login Successfully!</b>')
        else:
            return await sendMessage(message, '<b>Invalid Password!</b>\n\nKindly put the correct Password .')
    else:
        await sendMessage(message, '<b>Bot Login Usage :</b>\n\n<code>/cmd {password}</code>')


async def restart(_, message):
    restart_message = await sendMessage(message, "Restarting...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    for interval in [QbInterval, Interval]:
        if interval:
            interval[0].cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec('pkill', '-9', '-f', '-e', 'gunicorn|buffet|openstack|render|zcl')
    proc2 = await create_subprocess_exec('python3', 'update.py')
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")

@new_thread
async def ping(_, message):
    start_time = monotonic()
    reply = await sendMessage(message, BotTheme('PING'))
    end_time = monotonic()
    ping_time = int((end_time - start_time) * 1000)
    await editMessage(reply, BotTheme('PING_VALUE', value=(end_time - start_time)))

async def log(_, message):
    buttons = ButtonMaker()
    buttons.ibutton('📑 Log Display', f'wzmlx {message.from_user.id} logdisplay')
    await sendFile(message, 'Z_Logs.txt', buttons=buttons.build_menu(1))

async def search_images():
    if config_dict['IMG_SEARCH']:
        try:
            query_list = config_dict['IMG_SEARCH']
            total_pages = config_dict['IMG_PAGE']
            base_url = "https://www.wallpaperflare.com/search"

            for query in query_list:
                query = query.strip().replace(" ", "+")
                for page in range(1, total_pages + 1):
                    url = f"{base_url}?wallpaper={query}&width=1280&height=720&page={page}"
                    r = rget(url)
                    soup = BeautifulSoup(r.text, "html.parser")
                    images = soup.select('img[data-src^="https://c4.wallpaperflare.com/wallpaper"]')
                    for img in images:
                        img_url = img['data-src']
                        if img_url not in config_dict['IMAGES']:
                            config_dict['IMAGES'].append(img_url)
            if len(config_dict['IMAGES']) != 0:
                config_dict['STATUS_LIMIT'] = 2
            if DATABASE_URL:
                await DbManger().update_config({'IMAGES': config_dict['IMAGES'], 'STATUS_LIMIT': config_dict['STATUS_LIMIT']})
        except Exception as e:
            LOGGER.error(f"An error occurred: {e}")


help_string =  f'''<b><i>㊂ Help Guide :</i></b>

<b>NOTE: Click on any CMD to see more detalis.</b>

<b>Use Mirror commands to download your link/file/rcl</b>
➥ /{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Download via file/url/media to Upload to Cloud Drive.

<b>Use qBit commands for torrents only:</b>
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Download using qBittorrent and Upload to Cloud Drive.
/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CategorySelect}: Change upload category for Google Drive.

<b>Use Yt-Dlp commands for YouTube or any videos:</b>
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.

<b>Use Leech commands for upload to Telegram:</b>
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Upload to Telegram.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Download using qBittorrent and upload to Telegram(For torrents only).
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Download using Yt-Dlp(supported link) and upload to telegram.

/leech{BotCommands.DeleteCommand} [telegram_link]: Delete replies from telegram (Only Owner & Sudo).

<b>G-Drive commands:</b>
/{BotCommands.CloneCommand}: Copy file/folder to Cloud Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).
➥ /{BotCommands.GDCleanCommand[0]} or /{BotCommands.GDCleanCommand[1]} [drive_id]: Delete all files from specific folder in Google Drive.

<b>Cancel Tasks:</b>
/{BotCommands.CancelMirror}: Cancel task by gid or reply.
/{BotCommands.CancelAllCommand[0]} : Cancel all tasks which added by you /{BotCommands.CancelAllCommand[1]} to in bots.

<b>Torrent/Drive Search:</b>
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.

<b>Bot Settings:</b>
/{BotCommands.UserSetCommand}: Open User settings.
/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).
/{BotCommands.BotSetCommand}: Open Bot settings (Only Owner & Sudo).

<b>Authentication:</b>
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).

<b>Bot Stats:</b>
➥ /{BotCommands.BroadcastCommand[0]} or /{BotCommands.BroadcastCommand[1]} [reply_msg]: Broadcast to PM users who have started the bot anytime.
/{BotCommands.StatusCommand[0]} or /{BotCommands.StatusCommand[1]}: Shows a status of all active tasks.
/{BotCommands.StatsCommand[0]} or /{BotCommands.StatsCommand[1]}: Show server stats.
/{BotCommands.PingCommand[0]} or /{BotCommands.PingCommand[1]}: Check how long it takes to Ping the Bot.

<b>Maintainance:</b>
/{BotCommands.RestartCommand[0]}: Restart and update the bot (Only Owner & Sudo).
/{BotCommands.RestartCommand[1]}: Restart and update all bots (Only Owner & Sudo).
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).

<b>Executors:</b>
➥ /{BotCommands.ShellCommand}: Run shell commands (Only Owner).
➥ /{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).
➥ /{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).
➥ /{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).
➥ /exportsession: Generate User StringSession of Same Pyro Version (Only Owner).

<b>Extras:</b>
➥ /{BotCommands.SpeedCommand[0]} or /{BotCommands.SpeedCommand[1]}: Check Speed in VPS/Server.
➥ /{BotCommands.AddImageCommand} [url/photo]: Add Images in Bot
➥ /{BotCommands.ImagesCommand}: Generate grid of Stored Images.
➥ /{BotCommands.MediaInfoCommand[0]} or /{BotCommands.MediaInfoCommand[1]} [url/media]: Generate MediaInfo of Media or DL Urls

<b>Movie/TV Shows/Drama Search:</b>
➥ /{BotCommands.IMDBCommand}: Search in IMDB.
➥ /{BotCommands.AniListCommand}: Search for anime in AniList.
➥ /{BotCommands.AnimeHelpCommand}: Anime help guide.
➥ /{BotCommands.MyDramaListCommand}: Search in MyDramaList.


<b>RSS Feed:</b>
/{BotCommands.RssCommand}: Open RSS Menu.

<b>Attention: Read the first line again!</b>
'''

@new_thread
async def bot_help(_, message):
    reply_message = await sendMessage(message, help_string)
    await auto_delete_message(message, reply_message)


async def restart_notification():
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith(BotTheme('RESTART_SUCCESS')):
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=msg)
                await bot.send_message(chat_id, msg, disable_web_page_preview=True, reply_to_message_id=msg_id)
                await aioremove(".restartmsg")
            else:
                await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True,
                                       disable_notification=True)
        except Exception as e:
            LOGGER.error(e)
    if DATABASE_URL:
        if INCOMPLETE_TASK_NOTIFIER and (notifier_dict := await DbManger().get_incomplete_tasks()):
            for cid, data in notifier_dict.items():
                msg = BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y'), timz=config_dict['TIMEZONE'], version=get_version()) if cid == chat_id else BotTheme('RESTARTED')
                for tag, links in data.items():
                    msg += f"\n\n👤 {tag} Do your tasks again. \n"
                    for index, link in enumerate(links, start=1):
                        msg += f" {index}: {link} \n"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg)


        if STOP_DUPLICATE_TASKS:
            await DbManger().clear_download_links()


    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y'), timz=config_dict['TIMEZONE'], version=get_version()))
        except:
            pass
        await aioremove(".restartmsg")


async def main():
    await gather(start_cleanup(), torrent_search.initiate_search_tools(), restart_notification(), set_commands(bot))
    await sync_to_async(start_aria2_listener, wait=False)

    bot.add_handler(MessageHandler(
        start, filters=command(BotCommands.StartCommand) & private))
    bot.add_handler(CallbackQueryHandler(
        token_callback, filters=regex(r'^pass')))
    bot.add_handler(MessageHandler(
        login, filters=command(BotCommands.LoginCommand) & private))
    bot.add_handler(MessageHandler(log, filters=command(
        BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(
        BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(
        BotCommands.PingCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(bot_help, filters=command(
        BotCommands.HelpCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(stats, filters=command(
        BotCommands.StatsCommand) & CustomFilters.authorized))
    LOGGER.info("Congratulations, Bot Started Successfully!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()
