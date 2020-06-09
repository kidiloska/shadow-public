import html
import json
import os
import psutil
import random
import random
import datetime
from typing import Optional, List
import re
import requests
from telegram.error import BadRequest
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram import ChatAction


from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html
from shadow.modules.helper_funcs.chat_status import user_admin, sudo_plus, is_user_admin
from shadow import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, DEV_USERS, WHITELIST_USERS
from shadow.__main__ import STATS, USER_INFO, TOKEN

from telegram import Message, Chat, Update, Bot, MessageEntity
from shadow import dispatcher
from shadow.modules.disable import DisableAbleCommandHandler, DisableAbleRegexHandler
from shadow.modules.helper_funcs.extraction import extract_user
from shadow.modules.helper_funcs.filters import CustomFilters
import shadow.modules.sql.users_sql as sql
import shadow.modules.helper_funcs.cas_api as cas


@run_async
def whois(bot: Bot, update: Update, args: List[str]):
    bot.sendChatAction(update.effective_chat.id, "typing")
    message = update.effective_message
    chat = update.effective_chat
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not message.reply_to_message and not args:
        user = message.from_user

    elif not message.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not message.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        message.reply_text("I can't extract a user from this.")
        return

    else:
        return
    
    text = (f"<b>User Information:</b>\n"
            f"🆔: <code>{user.id}</code>\n"
            f"👤Name: {html.escape(user.first_name)}")

    if user.last_name:
        text += f"\n🚹Last Name: {html.escape(user.last_name)}"

    if user.username:
        text += f"\n♻️Username: @{html.escape(user.username)}"

    text += f"\n☣️Permanent user link: {mention_html(user.id, 'link🚪')}"

    num_chats = sql.get_user_num_chats(user.id)
    text += f"\n🌐Chat count: <code>{num_chats}</code>"
    text += "\n🎭Number of profile pics: {}".format(bot.get_user_profile_photos(user.id).total_count)
   
    try:
        user_member = chat.get_member(user.id)
        if user_member.status == 'administrator':
            result = requests.post(f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={chat.id}&user_id={user.id}")
            result = result.json()["result"]
            if "custom_title" in result.keys():
                custom_title = result['custom_title']
                text += f"\n🛡This user holds the title⚜️ <b>{custom_title}</b> here."
    except BadRequest:
        pass

   

    if user.id == OWNER_ID:
        text += "\n🚶🏻‍♂️Uff,This person is my Owner🤴\nI would never do anything against him!."
        
    elif user.id in DEV_USERS:
        text += "\n🚴‍♂️Pling,This person is my dev🤷‍♂️\nI would never do anything against him!."
        
    elif user.id in SUDO_USERS:
        text += "\n🚴‍♂️Pling,This person is one of my sudo users! " \
                    "Nearly as powerful as my owner🕊so watch it.."
        
    elif user.id in SUPPORT_USERS:
        text += "\n🚴‍♂️Pling,This person is one of my support users! " \
                        "Not quite a sudo user, but can still gban you off the map."
        
  
       
    elif user.id in WHITELIST_USERS:
        text += "\n🚴‍♂️Pling,This person has been whitelisted! " \
                        "That means I'm not allowed to ban/kick them."
    


    text +="\n"
    text += "\nCAS banned: "
    result = cas.banchecker(user.id)
    text += str(result)
    for mod in USER_INFO:
        if mod.__mod_name__ == "WHOIS":
            continue

        try:
            mod_info = mod.__user_info__(user.id)
        except TypeError:
            mod_info = mod.__user_info__(user.id, chat.id)
        if mod_info:
            text += "\n" + mod_info
    try:
        profile = bot.get_user_profile_photos(user.id).photos[0][-1]
        bot.sendChatAction(chat.id, "upload_photo")
        bot.send_photo(chat.id, photo=profile, caption=(text), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except IndexError:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)



SFW_STRINGS = (
    "🎶 മിഴിയറിയാതെ വന്നു നീ മിഴിയൂഞ്ഞാലിൽ... കനവറിയാതെയേതോ കിനാവു പോലെ... 🎶.",
    "🎶 നിലാവിന്റെ നീലഭസ്മ കുറിയണിഞ്ഞവളേ... കാതിലോലക്കമ്മലിട്ടു കുണുങ്ങി നിന്നവളേ... 🎶",
    "🎶 എന്തിനു വേറൊരു സൂര്യോദയം... നീയെൻ പൊന്നുഷസ്സന്ധ്യയല്ലേ... 🎶", 
    "🎶 ശ്രീരാഗമോ തേടുന്നിതെൻ വീണതൻ പൊൻ തന്ത്രിയിൽ... 🎶", 
    "🎶 മഴത്തുള്ളികൾ പൊഴിഞ്ഞീടുമീ നാടൻ വഴി... നനഞ്ഞോടിയെൻ കുടക്കീഴിൽ നീ വന്ന നാൾ... 🎶", 
    "🎶 നീയൊരു പുഴയായ് തഴുകുമ്പോൾ ഞാൻ പ്രണയം വിടരും കരയാവും... 🎶", 
    "🎶 അല്ലിമലർ കാവിൽ പൂരം കാണാൻ... അന്നു നമ്മൾ പോയി രാവിൽ നിലാവിൽ... 🎶", 
    "🎶 നിലാവിന്റെ നീലഭസ്മ കുറിയണിഞ്ഞവളേ... കാതിലോലക്കമ്മലിട്ടു കുണുങ്ങി നിന്നവളേ... 🎶", 
    "🎶 ചന്ദനച്ചോലയിൽ മുങ്ങിനീരാടിയെൻ ഇളമാൻ കിടാവേ ഉറക്കമായോ... 🎶", 
    "🎶 അന്തിപ്പൊൻവെട്ടം കടലിൽ മെല്ലെത്താഴുമ്പോൾ... മാനത്തെ മുല്ലത്തറയില് മാണിക്യച്ചെപ്പ്... 🎶", 
    "🎶 താമരപ്പൂവിൽ വാഴും ദേവിയല്ലോ നീ... പൂനിലാക്കടവിൽ പൂക്കും പുണ്യമല്ലോ നീ... 🎶", 
    "🎶 കുന്നിമണിച്ചെപ്പു തുറന്നെണ്ണി നോക്കും നേരം, പിന്നിൽവന്നു കണ്ണു പൊത്തും കള്ളനെങ്ങു പോയി... 🎶", 
    "🎶 ശ്യാമാംബരം പുൽകുന്നൊരാ വെൺചന്ദ്രനായ് നിൻ പൂമുഖം... 🎶", 
    "🎶 പാടം പൂത്തകാലം പാടാൻ വന്നു നീയും... 🎶", 
    "🎶 കറുകവയൽ കുരുവീ... മുറിവാലൻ കുരുവീ... തളിർ വെറ്റിലയുണ്ടോ... വരദക്ഷിണ വെക്കാൻ... 🎶", 
    "🎶 പത്തുവെളുപ്പിന് മുറ്റത്തു നിക്കണ കസ്തൂരി മുല്ലയ്ക്ക് കാത്തുകുത്ത്... എന്റെ കസ്തൂരി മുല്ലയ്ക്ക് കാത്തുകുത്ത്.. 🎶", 
    "🎶 മഞ്ഞൾ പ്രസാദവും നെറ്റിയിൽ ചാർത്തി... മഞ്ഞക്കുറിമുണ്ടു ചുറ്റി... 🎶", 
    "🎶 കറുത്തപെണ്ണേ നിന്നെ കാണാഞ്ഞിട്ടൊരു നാളുണ്ടേ... 🎶",
  )

@run_async
def sing(bot: Bot, update: Update):
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send messages
    message =  update.effective_message
    if message.reply_to_message:
      message.reply_to_message.reply_text(random.choice(SFW_STRINGS))
    else:
      message.reply_text(random.choice(SFW_STRINGS))
    
    
KILL_STRINGS = (
      "ഇരുട്ട് നിറഞ്ഞ എന്റെ ഈ ജീവിതത്തിലേക്ക് ഒരു തകർച്ചയെ ഓർമ്മിപ്പിക്കാൻ എന്തിന് ഈ ഓട്ടക്കാലണ ആയി നീ വന്നു 😖",
      "നമ്മൾ നമ്മൾ പോലുമറിയാതെ അധോലോകം ആയി മാറിക്കഴിഞ്ഞിരിക്കുന്നു ഷാജിയേട്ടാ...😐",
      "എന്നെ ചീത്ത വിളിക്കു... വേണമെങ്കിൽ നല്ല ഇടി ഇടിക്കു... പക്ഷെ ഉപദേശിക്കരുത്.....😏",
      "ഓ ബ്ലഡി ഗ്രാമവാസീസ്!😡",
      "സീ മാഗ്ഗി ഐ ആം ഗോയിങ് ടു പേ ദി ബിൽ.🤑",
      "പോരുന്നോ എന്റെ കൂടെ!😜",
      "തള്ളെ കലിപ്പ് തീരണില്ലല്ലോ!!🤬",
      "ഞാൻ കണ്ടു...!! കിണ്ടി... കിണ്ടി...!🤣",
      "മോന്തയ്ക്കിട്ട് കൊടുത്തിട്ട് ഒന്ന് എടുത്ത് കാണിച്ചുകൊടുക്ക് അപ്പോൾ കാണും ISI മാർക്ക് 😑",
      "ഡേവീസേട്ട, കിങ്ഫിഷറിണ്ടാ... ചിൽഡ്...! .",
      "പാതിരാത്രിക്ക് നിന്റെ അച്ഛൻ ഉണ്ടാക്കി വെച്ചിരിക്കുന്നോ പൊറോട്ടയും ചിക്കനും....😬",
      "ഇത് ഞങ്ങളുടെ പണിസാധനങ്ങളാ രാജാവേ.🔨⛏",
      "കളിക്കല്ലേ കളിച്ചാൽ ഞാൻ തീറ്റിക്കുമെ പുളിമാങ്ങ....😎",
      "മ്മക്ക് ഓരോ ബിയറാ കാച്ചിയാലോ...🥂",
      "ഓ പിന്നെ നീ ഒക്കെ പ്രേമിക്കുമ്പോൾ അത് പ്രണയം.... നമ്മൾ ഒക്കെ പ്രേമിക്കുമ്പോൾ അത് കമ്പി...😩",
      "കള്ളടിക്കുന്നവനല്ലേ കരിമീനിന്റെ സ്വാദറിയു.....😋",
      "ഡാ വിജയാ നമുക്കെന്താ ഈ ബുദ്ധി നേരത്തെ തോന്നാതിരുന്നത്...!🙄",
      "ഇത്രേം കാലം എവിടെ ആയിരുന്നു....!🥰",
      "ദൈവമേ എന്നെ മാത്രം രക്ഷിക്കണേ....⛪",
      "എനിക്കറിയാം ഇവന്റെ അച്ഛന്റെ പേര് ഭവാനിയമ്മ എന്നാ....😂🤣🤣",
      "ഡാ ദാസാ... ഏതാ ഈ അലവലാതി.....😒",
      "ഉപ്പുമാവിന്റെ ഇംഗ്ലീഷ് സാൾട് മംഗോ ട്രീ.....🤔",
      "മക്കളെ.. രാജസ്ഥാൻ മരുഭൂമിയിലേക്ക് മണല് കയറ്റിവിടാൻ നോക്കല്ലേ.....🥵",
      "നിന്റെ അച്ഛനാടാ പോൾ ബാർബർ....🤒",
      "കാർ എൻജിൻ ഔട്ട് കംപ്ലീറ്റ്‌ലി.....🥵",
      "ഇത് കണ്ണോ അതോ കാന്തമോ...👀",
      "നാലാമത്തെ പെഗ്ഗിൽ ഐസ്‌ക്യൂബ്സ് വീഴുന്നതിനു മുൻപ് ഞാൻ അവിടെ എത്തും.....😉",
      "അവളെ ഓർത്ത് കുടിച്ച കല്ലും നനഞ്ഞ മഴയും വേസ്റ്റ്....💔",
      "എന്നോട് പറ ഐ ലവ് യൂ ന്ന്....😘",
      "അല്ല ഇതാര് വാര്യംപിള്ളിയിലെ മീനാക്ഷി അല്ലയോ... എന്താ മോളെ സ്കൂട്ടറില്....🙈 ",
      "കിട്ടിയ  പെണ്ണും  കാട്ടിയ  പെണ്ണും കൂടെ ഇല്ലേലും ജനിപ്പിച്ച പെണ്ണ് കാണും ആജീവനാന്തം 🤰🤱👩‍👦",
  )

@run_async
def kill(bot: Bot, update: Update):
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send messages
    message =  update.effective_message
    if message.reply_to_message:
      message.reply_to_message.reply_text(random.choice(KILL_STRINGS))
    else:
      message.reply_text(random.choice(KILL_STRINGS))
    
TIP_STRINGS = (
      "വ്യക്ഷം മനുഷ്യനോട് സങ്കടപ്പെട്ടു: എത്രയോ വർഷങ്ങളായി എത്രയോ ചില്ലവെട്ടി എത്ര കുരിശുകൾ നിങ്ങൾ ഞങ്ങളിൽ നിന്ന് രൂപപ്പെടുത്തി, എന്നിട്ടും ഇനിയും നിങ്ങളിൽ നിന്നൊരു ക്രിസ്തു ഉണ്ടാകാഞ്ഞതന്തെ? ❤️",
      "എല്ലാ മതങ്ങളും തുടങ്ങിയിട്ടുള്ളത് ഏതെങ്കിലുമൊരു ഭൂപ്രദേശത്തിലെ ഒരു ജനതയുടെ താത്കാലികമായ ജീവിത പ്രശ്നങ്ങളോടുള്ള ആത്മീയ പ്രതികരണമായിട്ടാണ് അത് കൊണ്ട് എല്ലാ മതങ്ങള്‍ക്കും ജന്മനാ ഒരു എത്തനിക്ക് സ്വഭാവം ഉണ്ട് ❤️",
      "തീ പടര്‍ത്താനുഭയോഗിച്ച കമ്പോ കൊള്ളിയോ കത്തിത്തീര്‍ന്നാലും തീ പിന്നെയും പടര്‍ന്നുകൊണ്ടിരിക്കും. അഗ്നിഭാതയില്‍, ഒരു പക്ഷെ ചിന്തയുടെ അഗ്നിഭാതയില്‍ ആത്മനാശത്തിന്റെ അംശമുണ്ട്. അതിന്നര്‍ത്ഥം നിങ്ങള്‍ മറ്റുള്ളവരില്‍ പടരുന്നു എന്നോ സ്വയം ഇല്ലാതായിത്തീര്‍ന്നിട്ട് മറ്റുള്ളവരില്‍ ജീവിക്കുന്നു എന്നോ ആണ്. അതൊരു സാഫല്യമാണ് ❤️",
      "ഒരു നല്ല മുസ്ലീമും ഒരു നല്ല കമ്യൂണിസ്റ്റുകാരനും നല്ല ഹിന്ദുവുമൊക്കെയാകുന്നതില്‍ ഒരു തിന്മയുണ്ട് കാലത്തിനോടെന്ന പോലെ സ്വന്തത്തോടും അയാള്‍ നീതി ചെയ്യുന്നില്ല എന്നതാണത്. താന്‍ ജീവിക്കുന്ന കാലത്തിനോടാണ് ഒരുവന്‍റെ ആദ്യത്തെ പ്രതിബദ്ധത. എല്ലാ മതത്തിലേയും മൌലികവാദികള്‍ക്ക് പ്രതിബദ്ധത വേറൊരു കാലത്തിനോടാണ്. വേറൊരു കാലത്തുണ്ടായിട്ടുള്ള തത്വശാസ്ത്രത്തിനോടോ ഗ്രന്ഥങ്ങളോടോ ആണ്. ❤️",
      "നന്നായി അഭിനയിക്കാന്‍ കഴിയുന്നവനേ നല്ല കച്ചവടക്കാരനാകാന്‍ പറ്റു. സ്നേഹവും അടുപ്പവുമെല്ലാം ഭംഗിയായി അഭിനയിക്കണം .കഴുത്തറക്കുമ്പോഴും പുഞ്ചിരിക്കണം .ചതിക്കുമ്പോഴും സഹായിക്കുകയാണെന്നു തോന്നണം .നുണപറയുമ്പോഴും സത്യ പ്രഭാഷണംനടത്തുന്ന വിശുദ്ധന്റെ മുഖഭാവമായിരിക്കണം .ഒരിക്കിലും മുഖത്ത് ദേഷ്യം വരാന്‍ പാടില്ല ❤️",
      "സംതൃപ്തമായ യുവത്വം നിഷ്ക്രിയമായ യുവത്വവും നിര്ജീവമായ ജീവിതവുമായിത്തീരും... യുവത്വത്തിന് അതിന്റെ അസ്വസ്ഥത നഷ്ടപ്പെടുമ്പോള് അതൊരു യന്ത്രം പോലെ സമര്ത്ഥവും നിര്ജീവവും വന്ധ്യവും ആയിത്തീരും. വന്ധ്യതയ്ക്ക് ഒന്നിനെയും സൃഷ്ടിക്കുവാന് കഴിയാത്തതുകൊണ്ട് പുതിയ ഒരു ലോകക്രമത്തെ നിര്മ്മിക്കുവാനും അതിന് കഴിയില്ല. ❤️",
      "എത്രകോടി മനുഷ്യര്‍ വാഴുന്ന ഭൂമിയാണിത്. ഇതില്‍ നിങ്ങള്‍ക്കാരുമില്ലാ എന്നു കരയരുത്. അങ്ങനെ കരുതുന്നുണ്ടെങ്കില്‍ വിശ്വമാനവികതയുടെ ഹൃദയത്തെയാണ് നിങ്ങള്‍ ചോദ്യം ചെയ്യുക. ആരോ ഉണ്ട്... ജീവിതവുമായി നിങ്ങളെ ബന്ധിപ്പിക്കുന്ന അദൃശ്യമെങ്കിലും ദൃഢമായ ഏതോ കണ്ണി. എത്ര ദൂരെയായാലും സ്നേഹത്തിന്റെ കാന്തികഹൃദയത്തിലേക്ക് ചേര്‍ത്തു നിര്‍ത്തുന്ന ഒരു കണ്ണി... ❤️",
      "സൌന്ദര്യമൊ കരുത്തൊ കാരണം ഇഷ്ടപെട്ടുപോയ ഇണയെ എന്നെന്നേക്കും സ്വന്തമായി നിറുത്താന്‍ പ്രയോഗിക്കുന്ന തന്ത്രമാണ് പ്രണയ❤️ം",
      "ഇത്രയും കാലത്തെ അനുഭവത്തിൽനിന്നു പറയാം: ഭൂമിയിൽ മരണത്തേക്കാൾ അനിശ്ചിതത്വം പ്രണയത്തിന് മാത്രമേയുള്ളൂ.❤️",
      "ചിലരുടെ അസാന്നിധ്യത്തിലേ അവരുടെ വില നമുക്ക് മനസ്സിലാവൂ. അതുവരെ അവർ പരിഹസിക്കപ്പെടാനും സംശയിക്കപ്പെടാനും അവഗണിക്കപ്പെടാനും മാത്രമുള്ളവരാണ്.❤️",
      "ജീവിതത്തിന്റെ കാലവും പരിസരവും മാറുന്നതിനനുസരിച്ച് പുതിയ ബന്ധങ്ങളുണ്ടാകുന്നു. പുതിയ സൗഹൃദങ്ങൾ ഉണ്ടാവുന്നു. അപ്പോൾ പഴയവ നമുക്ക് അന്യമാകുന്നു. അവയെ നാം പടംപൊഴിച്ച് കളയുന്നു... ❤️",
      "ജീവിതത്തിന്റെ ഏറ്റവും പ്രതിസന്ധിഘട്ടത്തിൽ ആത്യന്തികമായി സത്യമെന്നും ശരിയെന്നും മനസ്സിന് തോന്നുന്നതുമാത്രം പ്രവർത്തിക്കുക. ആയിരംപേർ നിന്റെ പിന്നാലെ വരും, അവർ ആയിരം അഭിപ്രായങ്ങൾ പറയും. ആരുടെയും വാക്കുകൾക്കും പ്രലോഭനങ്ങൾക്കും ഒരിക്കലും വഴിപ്പെടാതെയിരിക്കുക.സത്യത്തിൽ ഉറച്ചുനിൽക്കുക. നീ വിജയിക്കുക തന്നെ ചെയ്യും... ❤️",
      "ശത്രുവിനെ സൃഷ്ടിക്കാതെ സ്നേഹം സൃഷ്ടിക്കുന്ന കലയാണ് മാനവികത ❤️",
      "ഒരു പൂവ് പൊട്ടിയ മഷിക്കുപ്പിയില് ­‍ വച്ചാലും ചളുങ്ങിയ ഒരു പൌഡര്‍ ടിന്നില്‍ വച്ചാലും അതൊക്കെ പൂപ്പാത്രമായി മാറുന്നത് പോലെ ഉള്ളിലൊരു പൂവുണ്ടാകുകയാണ് ­ പ്രധാനം. അകപൊരുളിന്റെ സുഗന്ധമാണ് സൗന്ദര്യം ❤️",
      "സംതൃപ്തമായ യുവത്വം നിഷ്ക്രിയമായ യുവത്വവും നിര്ജീവമായ ജീവിതവുമായിത്തീരും... യുവത്വത്തിന് അതിന്റെ അസ്വസ്ഥത നഷ്ടപ്പെടുമ്പോള് അതൊരു യന്ത്രം പോലെ സമര്ത്ഥവും നിര്ജീവവും വന്ധ്യവും ആയിത്തീരും. വന്ധ്യതയ്ക്ക് ഒന്നിനെയും സൃഷ്ടിക്കുവാന് കഴിയാത്തതുകൊണ്ട് പുതിയ ഒരു ലോകക്രമത്തെ നിര്മ്മിക്കുവാനും അതിന് കഴിയില്ല. ❤️",
  )

@run_async
def qt(bot: Bot, update: Update):
    bot.sendChatAction(update.effective_chat.id, "typing") # Bot typing before send messages
    message =  update.effective_message
    if message.reply_to_message:
      message.reply_to_message.reply_text(random.choice(TIP_STRINGS))
    else:
      message.reply_text(random.choice(TIP_STRINGS))
    


__help__ = """
❀ /sing Short Malayalam Song Lyrics🎶
❀ /kill Short movie dialouges 😎
❀ /qt Malayalam Quotes ❤️
❀ /whois Get user details 😎
"""



SING_HANDLER = DisableAbleCommandHandler("sing", sing)
KILL_HANDLER = DisableAbleCommandHandler("kill", kill)
TIP_HANDLER = DisableAbleCommandHandler("qt", qt)
WHOIS_HANDLER = DisableAbleCommandHandler("whois", whois, pass_args=True)

dispatcher.add_handler(SING_HANDLER)
dispatcher.add_handler(KILL_HANDLER)
dispatcher.add_handler(TIP_HANDLER)
dispatcher.add_handler(WHOIS_HANDLER)

__mod_name__ = "SH MOD"
__command_list__ = ["sing", "kill", "qt", "whois"]
__handlers__ = [SING_HANDLER, KILL_HANDLER, TIP_HANDLER, WHOIS_HANDLER]
