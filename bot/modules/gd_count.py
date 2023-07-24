from time import time

from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import (get_readable_file_size,
                                            get_readable_time, is_gdrive_link,
                                            new_task, sync_to_async)
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import deleteMessage, sendMessage
from bot.helper.themes import BotTheme

@new_task
async def countNode(_, message):
    args = message.text.split()
    if sender_chat := message.sender_chat:
        tag = sender_chat.title
    elif username := message.from_user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    link = args[1] if len(args) > 1 else ''
    if len(link) == 0 and (reply_to := message.reply_to_message):
        link = reply_to.text.split(maxsplit=1)[0].strip()

    if is_gdrive_link(link):
        sg = await sendMessage(message, BotTheme('COUNT_MSG', LINK=link))
        gd = GoogleDriveHelper()
        start_time = time()
        name, mime_type, size, files, folders = await sync_to_async(gd.count, link)
        elapsed = time() - start_time
        if mime_type is None:
            await sendMessage(message, name)
            return
        await deleteMessage(msg)
        msg = BotTheme('COUNT_NAME', COUNT_NAME=name)
        msg += BotTheme('COUNT_SIZE', COUNT_SIZE=get_readable_file_size(size))
        msg += BotTheme('COUNT_TYPE', COUNT_TYPE=mime_type)
        if mime_type == 'Folder':
            msg += BotTheme('COUNT_SUB', COUNT_SUB=folders)
            msg += BotTheme('COUNT_FILE', COUNT_FILE=files)
        msg += BotTheme('COUNT_CC', COUNT_CC=tag)
    else:
        msg = 'Send Gdrive link along with command or by replying to the link by command'
    if config_dict['DELETE_LINKS']:
        await deleteMessage(message.reply_to_message)
    await sendMessage(message, msg, photo='IMAGES')


bot.add_handler(MessageHandler(countNode, filters=command(
    BotCommands.CountCommand) & CustomFilters.authorized))
