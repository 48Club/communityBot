#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import re
import codecs
import logging
import json
import time
import datetime
import random
import ConfigParser
import thread
import threading
import requests
from telegram import *
from telegram.ext import *
from threading import Thread
from points import Points
from groupstat import GroupStat

reload(sys)  
sys.setdefaultencoding('utf8')


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


globalconfig = ConfigParser.ConfigParser()

# Read config
globalconfig.read(sys.argv[1])

# set bot conf
bottoken = globalconfig.get("bot","token")
botid=int(bottoken.split(":")[0])
botname = globalconfig.get("bot","name")

updater = Updater(token=bottoken, request_kwargs={'read_timeout': 30, 'connect_timeout': 10})

ALLGROUPS = {}
ALLBROADCASTEES = {}
ALLINFOS = {}
GROUPS = {}
GROUPADMINS = {}
CONFADMINS= [420909210]
DATAADMINS= [420909210]
CODEBONUS={}
BinanceCN = -1001136071376
GROUPSTAT = GroupStat(BinanceCN)
pointscore= Points('_data/points.db')

welcomelock = threading.Lock()

#BNB48 Test = -1001395548149

INVITINGS = {}
INVITERS = []

#for forwarding
CHANNELID=0
MESSAGEID=0

def loadJson(filename,default=[]):
    try:
        file=open(filename,"r")
        lastData = json.load(file)
        file.close()
        return lastData
    except:
        return default

def saveJson(filename,content):
    file = codecs.open(filename,"w","utf-8")
    file.write(json.dumps(content))
    file.flush()
    file.close()

LOCALES=loadJson("_data/locales.json",{})
infoBlackList = loadJson("_data/infoblacklist.json",[])

SPAMKEYWORDS = loadJson("_data/spamkeywords.json",[])
ACTIVITYENABLED=[]

def loadConfig(globalconfig,first=True):
    SPAMKEYWORDS = loadJson("_data/spamkeywords.json",[])
    globalconfig.read(sys.argv[1])

    global bottoken
    global botid
    global botname
    global CONFADMINS
    global DATAADMINS
    global GROUPS
    global ALLGROUPS
    global ALLBROADCASTEES
    global GROUPADMINS
    global updater
    global CODEBONUS


    # read ADMINS
    if globalconfig.has_section("confadmins"):
        for confadmin in globalconfig.items("confadmins"):
            if not int(confadmin[0]) in CONFADMINS:
                CONFADMINS.append(int(confadmin[0]))
    if globalconfig.has_section("dataadmins"):
        for dataadmin in globalconfig.items("dataadmins"):
            if not int(dataadmin[0]) in DATAADMINS:
                DATAADMINS.append(int(dataadmin[0]))
    # parse codebonus.json
    try:
        file = open("_data/codebonus.json")
        CODEBONUS = json.load(file)
        file.close()
    except:
        pass
    # parse broadcast info
    ALLBROADCASTEES={}
    for broadcastee in globalconfig.items("broadcast"):
        groupid = int(broadcastee[0])
        ALLBROADCASTEES[groupid]=broadcastee[1]
    # parse groups info
    for groupinfo in globalconfig.items("groups"):
        groupid = int(groupinfo[0])
        if re.search("\.json$",groupinfo[1]) is None:
            ALLGROUPS[groupid]=groupinfo[1]
            if groupid in GROUPS:
                del GROUPS[groupid]
            logger.warning("doesn't watch %s",groupid)
            continue
        try:
            file=open(groupinfo[1],"r")
            puzzles = json.load(file)
            file.close()
        except Exception as error:
            ALLGROUPS[groupid]=groupinfo[1]
            if groupid in GROUPS:
                del GROUPS[groupid]
            print(error)
            logger.warning("doesn't watch %s",groupid)
            continue
        if first:
            GROUPS[groupid]=puzzles
            GROUPS[groupid]['lasthintid']=0
            GROUPS[groupid]['ENTRANCE_PROGRESS']={}
            GROUPS[groupid]['kickjobs'] = {}
        else:
            oldgroup = GROUPS[groupid]
            GROUPS[groupid]=puzzles
            GROUPS[groupid]['lasthintid']=oldgroup['lasthintid']
            GROUPS[groupid]['ENTRANCE_PROGRESS']=oldgroup['ENTRANCE_PROGRESS']
            GROUPS[groupid]['kickjobs'] = oldgroup['kickjobs']
        ALLGROUPS[groupid]=GROUPS[groupid]['groupname']
        logger.warning("start watching %s",groupid)
    for each in globalconfig.items("activity"):
        if not int(each[0]) in ACTIVITYENABLED:
            ACTIVITYENABLED.append(int(each[0]))

CNYUSD = 6.899

def refreshInfos(bot,job):
    rawjson = requests.get('https://www.binance.com/info-api/v1/public/symbol/list').json()
    for eachcoin in rawjson['result']['data']:
        ALLINFOS[eachcoin['name']]=eachcoin
    ALLINFOS['KOGE']={
        "name":"KOGE",
        "fullName":"BNB48 Club®️ Points",
        "url":"https://bnb48.club",
        "price":100,
        "dayChange":10,
        "marketCap":527465,
        "tradeUrl":"https://www.binance.com/en/trade/KOGE_BNB",
        "volume":30274,
        "rank":ALLINFOS['BNB']['rank']+1000
    }
    rawjson = requests.get('https://www.binance.com/exchange/public/cnyusd').json()
    global CNYUSD
    CNYUSD = rawjson['rate']
    
def refreshAdmins(bot,job):
    global ALLGROUPS
    global GROUPADMINS
    GROUPSTAT.logMembersAcount(bot.getChatMembersCount(BinanceCN))
    GROUPSTAT._save()
    logger.warning("start refreshing")
    for groupid in ALLGROUPS:
        GROUPADMINS[groupid]=getAdminsInThisGroup(groupid)
    logger.warning("admins refreshed")

def reportInAllGroups(userid,fullname):
    logger.warning("this is reportInAllGroups")
    global DATAADMINS
    try:
        file=open("_data/blacklist_ids.json","r")
        BLACKLIST=json.load(file)["ids"]
        file.close()
    except IOError:
        BLACKLIST=[]
    if userid in BLACKLIST:
        finalmarkup=InlineKeyboardMarkup(
            [InlineKeyboardButton(
                'Unban',
                callback_data="banInAllGroups({},False)".format(userid))
            ]
        )
    else:
        finalmarkup=InlineKeyboardMarkup(
            [InlineKeyboardButton(
                'Ban',
                callback_data="banInAllGroups({},True)".format(userid))
            ]
        )
        
    for adminid in DATAADMINS:
        logger.warning(adminid)
        try:
            updater.bot.sendMessage(
                adminid,
                "Someone reported [{}](tg://user?id={})".format(fullname,userid),
                reply_markup=finalmarkup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(e)

def banInAllGroups(userid,op=True):
    thread = Thread(target = actualBanInAllGroups, args=[int(userid),op])
    thread.start()

def actualBanInAllGroups(userid,op):
    try:
        file=open("_data/blacklist_ids.json","r")
        BLACKLIST=json.load(file)["ids"]
        file.close()
    except IOError:
        BLACKLIST=[]
    if op:
        if not userid in BLACKLIST:
            BLACKLIST.append(userid)
    else:
        if userid in BLACKLIST:
            BLACKLIST.remove(userid)

    BLACKLIST=list(set(BLACKLIST))

    file = codecs.open("_data/blacklist_ids.json","w","utf-8")
    file.write(json.dumps({"ids":BLACKLIST}))
    file.flush()
    file.close()
    logger.warning("blacklist_ids updated")

    global ALLGROUPS
    for groupid in ALLGROUPS:
        try:
            if op:
                ban(groupid,userid)
                logger.warning("{} banned in {}".format(userid,groupid))
            else:
                unban(groupid,userid)
                logger.warning("{} unbanned in {}".format(userid,groupid))
            time.sleep(1)
        except:
            pass

def ban(chatid,userid):
    clearPoint(userid,chatid)
    updater.bot.kickChatMember(chatid,userid)
def unban(chatid,userid):
    updater.bot.unbanChatMember(chatid,userid)
def mute(chatid,userid):
    clearPoint(userid,chatid)
    updater.bot.restrictChatMember(chatid,userid,ChatPermissions(can_send_messages=False))
def kick(chatid,userid):
    clearPoint(userid,chatid)
    updater.bot.kickChatMember(chatid,userid)
    updater.bot.unbanChatMember(chatid,userid)
def resetCodebonus(bot,job):
    global CODEBONUS
    file = codecs.open("_data/codebonus.json","w","utf-8")
    file.write("{}")
    file.flush()
    file.close()
    logger.warning("reset codebonus")

def watchdogkick(bot,job):
    logger.warning("%s(%s) is being kicked from %s",job.context['full_name'],job.context['userid'],job.context['groupid'])
    kick(job.context['groupid'],job.context['userid'])
    logger.warning("%s(%s) is kicked from %s",job.context['full_name'],job.context['userid'],job.context['groupid'])

def restrict(chatid,userid,minutes):
    clearPoint(userid,chatid)
    updater.bot.restrictChatMember(chatid,user_id=userid,can_send_messages=False,until_date=time.time()+int(float(minutes)*60))

def unrestrict(chatid,userid):
    updater.bot.restrictChatMember(chatid,user_id=userid,can_send_messages=True,can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)

def callbackHandler(bot,update):
    global GROUPS
    if "broadcastTo" in update.callback_query.data:
        global CHANNELID,MESSAGEID
        CHANNELID=update.callback_query.message.reply_to_message.chat_id
        MESSAGEID=update.callback_query.message.reply_to_message.message_id
        eval(update.callback_query.data)
        update.callback_query.answer('Done')
        update.callback_query.message.reply_text('Done')
        update.callback_query.message.edit_reply_markup(text=update.callback_query.message.text)
        return
    if "banInAllGroups" in update.callback_query.data:
        eval(update.callback_query.data)
        update.callback_query.answer('Done')
        update.callback_query.message.reply_text('Done')
        update.callback_query.message.edit_reply_markup(text=update.callback_query.message.text)
        return
    if "reportInAllGroups" in update.callback_query.data:
        logger.warning(update.callback_query.data)
        eval(update.callback_query.data)
        update.callback_query.answer('reported')
        update.callback_query.message.reply_text('reported')
        update.callback_query.message.edit_reply_markup(text=update.callback_query.message.text)
        return

    thedata = update.callback_query.data.split("#")
    groupid = int(thedata[0])
    answer = thedata[1]
    message_id = update.callback_query.message.message_id
    activeuser = update.callback_query.from_user
    if not activeuser.id in GROUPS[groupid]['ENTRANCE_PROGRESS']:
        bot.sendMessage(activeuser.id,GROUPS[groupid]['onstart'])
        update.callback_query.answer()
        return

    ENTRANCE_PROGRESS = GROUPS[groupid]['ENTRANCE_PROGRESS']
    PUZZLES = GROUPS[groupid]['puzzles']

    currentpuzzleindex = ENTRANCE_PROGRESS[activeuser.id]
    #lasttext = PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['question']

    if answer == GROUPS[groupid]['puzzles'][currentpuzzleindex]['answer']:
    #correct answer
        update.callback_query.answer()
        update.callback_query.message.reply_text(GROUPS[groupid]['puzzles'][currentpuzzleindex]['postcorrect'])
        update.callback_query.message.edit_reply_markup(text=update.callback_query.message.text)
        

        if ENTRANCE_PROGRESS[activeuser.id] + 1>= len(GROUPS[groupid]['puzzles']):
            #all questions done
            if activeuser.id in GROUPS[groupid]['kickjobs']:
                GROUPS[groupid]['kickjobs'][activeuser.id].schedule_removal()
                del GROUPS[groupid]['kickjobs'][activeuser.id]
            if bot.getChatMember(groupid,activeuser.id).can_send_messages == False:
                unrestrict(groupid,activeuser.id)
                logger.warning("%s(%s)Past the test in %s",activeuser.full_name,activeuser.id,groupid)
                bot.sendMessage(activeuser.id, GROUPS[groupid]['onpast'])
            else:
                pass
        else:
            ENTRANCE_PROGRESS[activeuser.id]+=1
            bot.sendMessage(activeuser.id,PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['question'],reply_markup=buildpuzzlemarkup(groupid,PUZZLES[ENTRANCE_PROGRESS[activeuser.id]]['options']))
            
    else:
        #wrong answer
        update.callback_query.answer()
        update.callback_query.message.reply_text(GROUPS[groupid]['puzzles'][currentpuzzleindex]['postincorrect'])
        update.callback_query.message.edit_reply_markup(text=update.callback_query.message.text)
        update.callback_query.message.reply_text(GROUPS[groupid]['onfail'])
        del ENTRANCE_PROGRESS[activeuser.id]

    #update.callback_query.edit_message_text( text = lasttext)
            
def buildpuzzlemarkup(groupid,options):
    keys = []
    random.shuffle(options)
    for each in options:
        keys.append([InlineKeyboardButton(each[1],callback_data="{}#{}".format(groupid,each[0]))])
    return InlineKeyboardMarkup(keys)
    
def gunHandler(bot,update):
    if isAdmin(update,True,True,True):
        mute(update.message.chat_id,update.message.reply_to_message.from_user.id)
        delayMessageDelete(update.message.reply_to_message,0)    
    delayMessageDelete(update.message,0)    
def rmHandler(bot,update):
    if isAdmin(update,False,True,True):
        delayMessageDelete(update.message.reply_to_message,0)    
    delayMessageDelete(update.message,0)    

def replybanallHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    #ban(update.message.chat_id,update.message.reply_to_message.from_user.id)
    banInAllGroups(update.message.reply_to_message.from_user.id,True)
    update.message.reply_text("banned in all groups")
def idunbanallHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things=update.message.text.split(" ")
    banInAllGroups(things[1],False)
    update.message.reply_text("unbanned in all groups")
def batchbanallHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things=update.message.text.split(" ")
    for eachid in things[1].split("|"):
        banInAllGroups(eachid,True)
        time.sleep(60)
def idbanallHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things=update.message.text.split(" ")
    banInAllGroups(things[1],True)
    update.message.reply_text("banned in all groups")

def reportHandler(bot,update):
    things=update.message.text.split(" ")
    if len(things)>1:
        span=int(things[1])
    else:
        span=1
    update.message.reply_text(GROUPSTAT.getReport(span))
def spamHandler(bot,update):
    things=update.message.text.split(" ")
    if len(things) == 1:
        update.message.reply_text(str(SPAMKEYWORDS).encode('ascii').decode('unicode-escape'))
        return
    del things[0]
    for eachword in things:
        if not eachword in SPAMKEYWORDS:
            SPAMKEYWORDS.append(eachword)
            update.message.reply_text(eachword + " added")
        else:
            SPAMKEYWORDS.remove(eachword)
            update.message.reply_text(eachword + " removed")
    saveJson("_data/spamkeywords.json",SPAMKEYWORDS)
def reloadHandler(bot,update):
    global DATAADMINS
    global globalconfig
    if not isAdmin(update,False,True,False):
        return
    if update.message.chat.type != 'private':
        return

    loadConfig(globalconfig)
    update.message.reply_text("reloaded")

def deactivityHandler(bot,update):
    #only confadmin
    if not isAdmin(update,False,True,False):
        logger.warning("not admin")
        return
    if update.message.chat.type == "private":
        logger.warning("not group")
        return
    global globalconfig
    globalconfig.remove_option("activity",str(update.message.chat_id))
    with open(sys.argv[1], 'wb') as configfile:
        globalconfig.write(configfile)
        update.message.reply_text("activity removed")
    ACTIVITYENABLED.remove(update.message.chat_id)
    
def activityHandler(bot,update):
    #only confadmin
    if not isAdmin(update,False,True,False):
        logger.warning("not admin")
        return
    if update.message.chat.type == "private":
        logger.warning("not group")
        return
    tuples = update.message.text.split(" ")
    # /activity name start end
    #if len(tuples) != 4:
    #    logger.warning("not 4")
    #    return
    del tuples[0]
    global globalconfig
    globalconfig.set("activity",str(update.message.chat_id),"#".join(tuples))
    with open(sys.argv[1], 'wb') as configfile:
        globalconfig.write(configfile)
        update.message.reply_text("activity setted")
    ACTIVITYENABLED.remove(append.message.chat_id)
    

def decodebonusHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things = update.message.text.split(" ")
    if len(things) != 2:
        return
    code = things[1]
    global CODEBONUS
    if code in CODEBONUS:
        del CODEBONUS[code]
        file = codecs.open("_data/codebonus.json","w","utf-8")
        file.write(json.dumps(CODEBONUS))
        file.flush()
        file.close()
        update.message.reply_text("{} removed".format(code))
def codebonusHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things = update.message.text.split(" ")
    if len(things) != 2:
        return
    code = things[1]
    global CODEBONUS
    if not code in CODEBONUS:
        CODEBONUS[code]=[]
        file = codecs.open("_data/codebonus.json","w","utf-8")
        file.write(json.dumps(CODEBONUS))
        file.flush()
        file.close()
        update.message.reply_text("{} added".format(code))

def dataadminHandler(bot,update):
    global DATAADMINS
    global globalconfig
    targetuser = update.message.reply_to_message.from_user
    if not isAdmin(update,False,True,False):
        return
    if not targetuser.id in DATAADMINS:
        globalconfig.set("dataadmins",str(targetuser.id),targetuser.full_name)
        DATAADMINS.append(targetuser.id)
        with open(sys.argv[1], 'wb') as configfile:
            globalconfig.write(configfile)
        update.message.reply_text("{} is dataadmin now".format(targetuser.full_name))
    else:
        update.message.reply_text("was dataadmin before")
def broadcasteeHandler(bot,update):
    if not isAdmin(update,False,True,False):
        update.message.reply_text("no admin")
        return
    global globalconfig
    things = update.message.text.split(" ")
    if len(things) != 2:
        update.message.reply_text("/命令 语言")
        return
    groupid = update.message.chat_id
    ALLBROADCASTEES[groupid]=things[1]+"-"+update.message.chat.title
    globalconfig.set("broadcast",str(update.message.chat_id),things[1]+"-"+update.message.chat.title)
    with open(sys.argv[1], 'wb') as configfile:
        globalconfig.write(configfile)
    update.message.reply_text("Added as "+things[1]+" Broadcastee")

def superviseHandler(bot,update):
    if not isAdmin(update,False,True,False):
        return
    global globalconfig
    if not update.message.chat_id in ALLGROUPS:
        groupid = update.message.chat_id
        ALLGROUPS[groupid]=update.message.chat.title
        GROUPADMINS[groupid]=getAdminsInThisGroup(groupid)
        globalconfig.set("groups",str(update.message.chat_id),update.message.chat.title)
        with open(sys.argv[1], 'wb') as configfile:
            globalconfig.write(configfile)
        update.message.reply_text("supervised")
    else:
        update.message.reply_text("was supervised before")
def fwdbanallHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    targetuser = update.message.reply_to_message.forward_from
    banInAllGroups(targetuser.id,True)
    update.message.reply_text("banned in all groups")

def getAdminsInThisGroup(groupid):
    try:
        admins = updater.bot.get_chat_administrators(groupid)
    except:
        admins = []
    RESULTS=[]
    for admin in admins:
        RESULTS.append(admin.user.id)
    return RESULTS

def isAdmin(update,GROUPTrue=True,CONFTrue=True,DATATrue=True):
    global GROUPADMINS
    userid = update.message.from_user.id
    if GROUPTrue and update.message.chat_id in GROUPADMINS and userid in GROUPADMINS[update.message.chat_id]:
        return True
    elif CONFTrue and userid in CONFADMINS:
        return True
    elif DATATrue and userid in DATAADMINS:
        return True
    else:
        return False
def fileHandler(bot,update):
    filename = update.message.document.file_name
    if globalconfig.has_section("blackfiletypes"):
        for item in globalconfig.items("blackfiletypes"):
            if item[0] in filename:
                banInAllGroups(update.message.from_user.id,True)
                break
    if not ".mp4" in update.message.document.file_name:
        update.message.delete()
def debugHandler(bot,update):
    chatmember = bot.getChatMember(update.message.chat_id,update.message.reply_to_message.from_user.id)
    update.message.reply_text(chatmember.status)
    update.message.reply_text(chatmember.until_date)
def startHandler(bot,update):
    infoHandler(bot,update)
    #must in private mode
    if update.message.chat.type != 'private':
        return
    userid = update.message.from_user.id
    global GROUPS
    for groupid in GROUPS:
        try:
            chatmember = bot.getChatMember(groupid,userid)
            if chatmember.status != 'restricted':
                #if banned, no reentry
                continue
            elif chatmember.can_send_messages != False:
                # can send but just not that kind of
                continue
            elif not chatmember.until_date is None:
                # must be forever
                continue
            else:
                update.message.reply_text(GROUPS[groupid]['puzzles'][0]['question'],reply_markup=buildpuzzlemarkup(groupid,GROUPS[groupid]['puzzles'][0]['options']))
                GROUPS[groupid]['ENTRANCE_PROGRESS'][userid] = 0
                return
        except:
            continue
    update.message.reply_text("You've no new group test pending")
        
def cleanHandler(bot,update):
    if isAdmin(update,False,True,False):
        updater.job_queue.stop()
        for job in updater.job_queue.jobs():
            job.schedule_removal()
            if job.name in ['watchdogkick']:
                job.run(bot)
                logger.warning("job {} cleared".format(job.name))
        update.message.reply_text('cleaned')

        for groupid in GROUPS:
            bot.deleteMessage(groupid,GROUPS[groupid]['lasthintid'])
        #codebonus
        file = codecs.open("_data/codebonus.json","w","utf-8")
        file.write(json.dumps(CODEBONUS))
        file.flush()
        file.close()

        updater.stop()
        updater.is_idle = False
        os.exit()

def broadcastTo(thelang):
    for each in ALLBROADCASTEES:
        lang=ALLBROADCASTEES[each].split("-")[0]
        if lang == thelang:
            print(each)
            print(CHANNELID)
            print(MESSAGEID)
            updater.bot.forwardMessage(each,CHANNELID,MESSAGEID)
def localeHandler(bot,update):
    if isAdmin(update):
        things = update.message.text.split(" ")
        LOCALES[str(update.message.chat_id)]=things[1]
        saveJson("_data/locales.json",LOCALES)
        update.message.reply_text(things[1]);
def delayMessageDelete(message,seconds=60):
    thread = Thread(target = actualMessageDelete, args=[message,seconds])
    thread.start()
def actualMessageDelete(message,seconds):
    time.sleep(seconds)
    try:
        message.delete()
    except:
        pass

def infoHandler(bot,update):    
    if not '?' in update.message.text and not '？' in update.message.text:
        return
    coin = update.message.text.strip('?？').upper()
    if "STOPQUERY" == coin and isAdmin(update,True,True,True):
        infoBlackList.append(update.effective_chat.id)
        saveJson("_data/infoblacklist.json",infoBlackList)
        update.effective_message.reply_text("⛔️")
        return
    if "STARTQUERY" == coin and isAdmin(update,True,True,True):
        infoBlackList.remove(update.effective_chat.id)
        saveJson("_data/infoblacklist.json",infoBlackList)
        update.effective_message.reply_text("✅")
        return
    if update.effective_chat.id in infoBlackList:
        return
    locales={"en":{"price":"Price","rank":"Rank","volume":"Volume(24H)","marketcap":"Market Cap","detail":"More Details on {}","trade":"Trade {} on Binance","lang":"en","currency":"$","rate":1},"zh":{"price":"现价","rank":"排名","marketcap":"市值","volume":"日成交额","detail":"更多资料","trade":"立即交易","lang":"cn","currency":"￥","rate":CNYUSD}}

    if str(update.message.chat_id) in LOCALES and ('zh' in LOCALES[str(update.message.chat_id)] or 'cn' in LOCALES[str(update.message.chat_id)]) :
        locale=locales['zh']
    else:
        locale=locales['en']
    if coin in ALLINFOS:
        if ALLINFOS[coin]['dayChange']>0:
            symbol="📈"
        else:
            symbol="📉"
        info="*{}*({})\n*{}*: {} {}  *(*{}{}%*)*\n*{}*: {}".format(
            ALLINFOS[coin]['fullName'],
            ALLINFOS[coin]['name'],
            locale['price'],
            locale['currency'],
            ALLINFOS[coin]['price']*locale['rate'],
            symbol,
            round(ALLINFOS[coin]['dayChange'],2),
            locale['rank'],
            ALLINFOS[coin]['rank']
        )
        if 'marketCap' in ALLINFOS[coin]:
            info += "\n*{}*: {}{}".format(locale['marketcap'],locale['currency'],format(int(ALLINFOS[coin]['marketCap']*locale['rate']),','))
        if 'volumeGlobal' in ALLINFOS[coin]:
            info += "\n*{}*: {}{}".format(locale['volume'],locale['currency'],format(int(ALLINFOS[coin]['volumeGlobal']*locale['rate']),','))
        elif 'volume' in ALLINFOS[coin]:
            info += "\n*{}*: {}{}".format(locale['volume'],locale['currency'],format(int(ALLINFOS[coin]['volume']*locale['rate']),','))

        #info += "\n---\n_Powered By_  [BNB48 Club®️](https://bnb48.club)"

        if "http" in ALLINFOS[coin]['url']:
            buttons = [[InlineKeyboardButton(locale['detail'].format(coin),url=ALLINFOS[coin]['url'])]]
        else:
            buttons = [[InlineKeyboardButton(locale['detail'].format(coin),url="https://info.binance.com/{}/currencies/{}?utm_source=tgbot".format(locale['lang'],ALLINFOS[coin]['url']))]]
        if 'tradeUrl' in ALLINFOS[coin]:
            #buttons.append([InlineKeyboardButton(locale['trade'].format(coin),url=ALLINFOS[coin]['tradeUrl']+'?ref=10150829')])
            buttons.append([InlineKeyboardButton(locale['trade'].format(coin),url=ALLINFOS[coin]['tradeUrl']+'?utm_source=tgbot')])

        delayMessageDelete(update.message.reply_markdown(
            text=info,
            quote=False,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        ))
        delayMessageDelete(update.message,10)
        '''
        try:
            update.message.delete()
        except:
            pass
        '''
def forwardHandler(bot,update):
    global ALLGROUPS
    global GROUPADMINS
    fwduser = update.message.forward_from
    '''
    suspectScam = False
    if globalconfig.has_section("scamkeys"):
        for scamkey in globalconfig.items("scamkeys"):
            if not fwduser is None and (not re.search(scamkey[0],str(fwduser.username),re.IGNORECASE) is None or not re.search(scamkey[0],fwduser.full_name,re.IGNORECASE) is None):
                logger.warning("{}/{} Hit scam key {}".format(fwduser.username,fwduser.full_name,scamkey))
                suspectScam = True
                break
    '''
    #if  
    if update.message.chat.type == 'private':# or suspectScam:
        #send in private 
        # conf admin, broadcast
        if not update.message.forward_from_chat is None and isAdmin(update,False,True,False):
            Langs={}
            for each in ALLBROADCASTEES:
                lang=ALLBROADCASTEES[each].split("-")[0]
                if not lang in Langs:
                    Langs[lang]=[]
                Langs[lang].append(each)
            broadcast_markup=[]
            for eachlang in Langs:
                broadcast_markup.append(
                    [
                        InlineKeyboardButton('转发至'+eachlang+'的'+str(len(Langs[eachlang]))+'个群组',callback_data="broadcastTo('{}')".format(eachlang))
                    ]
                )
            update.message.reply_text(
                    "点击群发到对应的群组",
                    reply_markup=InlineKeyboardMarkup(broadcast_markup),
                    quote=True
                )
            return


        #hint scam
        fwdisAdmin = False
        response=""
        for groupid in ALLGROUPS:
            if not fwduser is None and fwduser.id in GROUPADMINS[groupid]:
                fwdisAdmin = True
                response+="✅✅Admin in {}".format(ALLGROUPS[groupid])
                response+="\n"
        if isAdmin(update,False,True,True):
            thismarkup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('Ban in all groups!',callback_data="banInAllGroups({},True)".format(fwduser.id))],
                        [InlineKeyboardButton('Unban in all groups!',callback_data="banInAllGroups({},False)".format(fwduser.id))]
                    ])
        elif not fwdisAdmin:
            thismarkup=InlineKeyboardMarkup([
                        [InlineKeyboardButton('Report!',callback_data="reportInAllGroups({},'{}')".format(fwduser.id,fwduser.full_name))]
                    ])
        else:
            thismarkup = None

        if fwdisAdmin:
            if update.message.chat.type == 'private':
                update.message.reply_text(response,reply_markup=thismarkup)
        else:
            if isAdmin(update,False,True,True):
                update.message.reply_text(
                    "‼️ Be careful, this guy is not an admin",
                    reply_markup = thismarkup
                )
            else:
                update.message.reply_text("‼️ Be careful, this guy is not an admin",reply_markup=thismarkup)

def textInGroupHandler(bot,update):
    infoHandler(bot,update)
    if not update.message.chat_id in ACTIVITYENABLED:
        return
    if update.message.chat_id == BinanceCN:
        GROUPSTAT.logMessage(update.message.from_user.id)
    if not isAdmin(update,True,False,False):
        pointscore.mine(update.message.from_user,update.message.chat_id)
    if update.message.text in CODEBONUS:
        if not update.message.from_user.id in CODEBONUS[update.message.text]:
            bonus = pointscore.bonus(update.message.from_user,update.message.chat_id)
            CODEBONUS[update.message.text].append(update.message.from_user.id)
            update.message.reply_text("➕{}💎".format(bonus))
            file = codecs.open("_data/codebonus.json","w","utf-8")
            file.write(json.dumps(CODEBONUS))
            file.flush()
            file.close()

    for word in SPAMKEYWORDS:
        if word in update.message.text:
            banInAllGroups(update.effective_user.id,True)
            logger.warning('%s|%s is banned from all groups because of spam',update.effective_user.id,update.effective_user.full_name)
            update.message.delete()
def clearPoint(uid,groupid):
    pointscore.clearUser(uid,groupid)
def pointsHandler(bot,update):
    if update.message.chat.type == 'private':
        return
    try:
        bot.sendMessage(update.message.from_user.id,"{}\n💎{}".format(update.message.chat.title,pointscore.getBalance(update.message.from_user.id,update.message.chat_id)))
    except:
        update.message.reply_text("{}\n💎.{}".format(update.message.chat.title,pointscore.getBalance(update.message.from_user.id,update.message.chat_id)))

    update.message.delete()
def punishHandler(bot,update):
    if not isAdmin(update,True,True,True):
        return
    if not update.message.reply_to_message is None:
        pointscore.clearUser(update.message.reply_to_message.from_user.id,update.message.chat_id)
        update.message.reply_markdown("{} 💎0".format(update.message.reply_to_message.from_user.mention_markdown()))
        if update.message.chat_id == BinanceCN:
            INVITINGS = loadJson("_data/invitings.json",{})
            if str(update.message.reply_to_message.from_user.id) in INVITINGS:
                pointscore.changeBalance(INVITINGS[str(update.message.reply_to_message.from_user.id)],None,BinanceCN,-1)

    
def clearpointsHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    pointscore.clearGroup(update.message.chat_id)
    update.message.reply_text("cleared")
def aboveHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things = update.message.text.split(" ")
    if len(things) != 2:
        return
    amount=int(things[1])
    res=""
    for tuple in pointscore.getAbove(update.message.chat_id,amount):
        res += "\n💎{}\t,[{}](tg://user?id={})".format(tuple[3],tuple[1],tuple[0])
    if len(res) > 0:
        update.message.reply_markdown(res,quote=False)
def topHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things = update.message.text.split(" ")
    if len(things) == 1:
        top=10
    else:
        top=int(things[1])
    res=""
    for tuple in pointscore.getBoard(update.message.chat_id,top):
        res += "\n💎{}\t,[{}](tg://user?id={})".format(tuple[3],tuple[1],tuple[0])
    if len(res) > 0:
        update.message.reply_markdown(res,quote=False)
def rankHandler(bot,update):
    if not isAdmin(update,False,True,True):
        return
    things = update.message.text.split(" ")
    if len(things) != 2:
        return
    
    rank=int(things[1])
    tuple=pointscore.getRank(update.message.chat_id,rank)
    res = "\n💎{}\t[{}](tg://user?id={})".format(tuple[3],tuple[1],tuple[0])
    update.message.reply_markdown(res,quote=True)

def onleft(bot,update):
    if update.message.chat_id == BinanceCN:
        INVITINGS = loadJson("_data/invitings.json",{})
        if str(update.message.left_chat_member.id) in INVITINGS:
            pointscore.changeBalance(INVITINGS[str(update.message.left_chat_member.id)],None,BinanceCN,-1)
        GROUPSTAT.logQuit(update.message.left_chat_member.id,update.message.effective_user.id)
def addHandler(bot,update):
    if not isAdmin(update,False,True,True):
        returnthings = update.message.text.split(" ")
    things = update.message.text.split(" ")
    if len(things) != 3:
        return
    uid = int(things[1])
    amount = int(things[2])
    pointscore.changeBalance(uid,None,BinanceCN,amount)
    update.message.reply_text("Done")

def welcome(bot, update):
    global GROUPS
    
    SPAMWORDS = loadJson("_data/blacklist_names.json")
    BLACKLIST = loadJson("_data/blacklist_ids.json")
    INVITINGS = loadJson("_data/invitings.json",{})
    INVITERS = loadJson("_data/inviters.json",[])
    

    for newUser in update.message.new_chat_members:
        if update.message.chat_id == BinanceCN:
            GROUPSTAT.logNewMember(newUser.id,update.effective_user.id)

        if newUser.id in BLACKLIST:
            ban(update.message.chat_id,newUser.id)
            logger.warning('%s|%s is banned from %s because of blacklist',newUser.id,newUser.full_name,update.message.chat.title)
            return
        for SPAMWORD in SPAMWORDS:
            if SPAMWORD in newUser.full_name:
                banInAllGroups(newUser.id,True)
                logger.warning('%s|%s is banned from all groups because of spam',newUser.id,newUser.full_name)
                return
        if  update.message.chat_id == BinanceCN and update.message.from_user.id != newUser.id and not newUser.is_bot and not str(newUser.id) in INVITINGS:
            pointscore.changeBalance(update.message.from_user.id,update.message.from_user.full_name,BinanceCN,1)
            INVITINGS[str(newUser.id)] = update.message.from_user.id
            saveJson("_data/invitings.json",INVITINGS)
            update.message.reply_text("{}邀请新用户{} ，挖到1积分".format(update.message.from_user.full_name,newUser.full_name))
            if not str(update.message.from_user.id) in INVITERS:
                INVITERS.append(str(update.message.from_user.id))
                saveJson("_data/inviters.json",INVITERS)
                update.message.reply_text("首次邀请新用户获得幸运抽奖机会，正在抽奖……",quote=False)
                if random.random() < 0.2:
                    pointscore.changeBalance(update.message.from_user.id,update.message.from_user.full_name,BinanceCN,1)
                    update.message.reply_markdown("{} 抽中幸运奖 请妥善保存本条消息作为领奖凭据。\n\n凭本条消息找到群内管理员/币安天使提交收货地址。\n\n管理员/天使绝对不会首先私聊你，谨防骗子".format(update.message.from_user.mention_markdown()),quote=False)
                else:
                    update.message.reply_text("未抽中幸运奖",quote=False)

    groupid = update.message.chat_id
    if groupid in GROUPS and "puzzles" in GROUPS[groupid]:
        for newUser in update.message.new_chat_members:
            newChatMember = bot.getChatMember(groupid,newUser.id)
            logger.warning("%s(%s)Joined %s",newUser.full_name,newUser.id,update.message.chat.title)
            if 'restricted' in newChatMember.status and not newChatMember.until_date is None:
                # if muted before, do nothing
                continue


            try:
                bot.sendMessage(newUser.id,GROUPS[groupid]['grouphint']+": /start")
            except:
                #pass
                logger.warning("send to %s(%s) failure",newUser.full_name,newUser.id)
                try:
                    if GROUPS[groupid]['lasthintid'] != 0:
                        try:
                            bot.deleteMessage(groupid,GROUPS[groupid]['lasthintid'])
                        except:
                            pass
                    GROUPS[groupid]['lasthintid'] = update.message.reply_text((GROUPS[groupid]['grouphint']+": {}").format(botname),quote=True).message_id
                except:
                    logger.warning("send and delete new hint exception")
            finally:
                restrict(update.message.chat_id,newUser.id,0.4)
                probation = GROUPS[groupid]['probation']
                GROUPS[groupid]['kickjobs'][newUser.id] = updater.job_queue.run_once(watchdogkick,probation*60,context = {"userid":newUser.id,"groupid":groupid,"full_name":newUser.full_name})
                logger.warning("%s minutes kicker timer started for %s in %s",GROUPS[groupid]['probation'],newUser.id,groupid)

            

    update.message.delete()
    

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)



class documentFilter(BaseFilter):
    def filter(self,message):
        if not message.document is None:
        #if message.animation is None and not message.document is None:
            return True
        else:
            return False

def main():
    """Start the bot."""
    loadConfig(globalconfig)
    logger.warning("%s(%s) starts watching",globalconfig.get("bot","name"),globalconfig.get("bot","token"))

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram

    dp.add_handler(CommandHandler( [ "points" ], pointsHandler))
    dp.add_handler(CommandHandler( [ "add" ], addHandler))
    dp.add_handler(CommandHandler( [ "rank" ], rankHandler))
    dp.add_handler(CommandHandler( [ "top" ], topHandler))
    dp.add_handler(CommandHandler( [ "above" ], aboveHandler))
    dp.add_handler(CommandHandler( [ "activity" ], activityHandler))
    dp.add_handler(CommandHandler( [ "deactivity" ], deactivityHandler))
    dp.add_handler(CommandHandler( [ "start" ], startHandler))
    dp.add_handler(CommandHandler( [ "debug" ], debugHandler))
    dp.add_handler(CommandHandler( [ "replybanall" ], replybanallHandler))
    dp.add_handler(CommandHandler( [ "batchbanall" ], batchbanallHandler))
    dp.add_handler(CommandHandler( [ "gun" ], gunHandler))
    dp.add_handler(CommandHandler( [ "rm" ], rmHandler))
    dp.add_handler(CommandHandler( [ "idbanall" ], idbanallHandler))
    dp.add_handler(CommandHandler( [ "idunbanall" ], idunbanallHandler))
    dp.add_handler(CommandHandler( [ "fwdbanall" ], fwdbanallHandler))
    dp.add_handler(CommandHandler( [ "supervise" ], superviseHandler))
    dp.add_handler(CommandHandler( [ "broadcastee" ], broadcasteeHandler))
    dp.add_handler(CommandHandler( [ "dataadmin" ], dataadminHandler))
    dp.add_handler(CommandHandler( [ "reload" ], reloadHandler))
    dp.add_handler(CommandHandler( [ "spam" ], spamHandler))
    dp.add_handler(CommandHandler( [ "report" ], reportHandler))
    dp.add_handler(CommandHandler( [ "clean" ], cleanHandler))
    dp.add_handler(CommandHandler( [ "clearpoints" ], clearpointsHandler))
    dp.add_handler(CommandHandler( [ "punish" ], punishHandler))
    dp.add_handler(CommandHandler( [ "ban" ], punishHandler))
    dp.add_handler(CommandHandler( [ "mute" ], punishHandler))
    dp.add_handler(CommandHandler( [ "codebonus" ], codebonusHandler))
    dp.add_handler(CommandHandler( [ "decodebonus" ], decodebonusHandler))
    dp.add_handler(CommandHandler( [ "locale" ], localeHandler))

    dp.add_handler(CallbackQueryHandler(callbackHandler))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))#'''处理新成员加入'''
    dp.add_handler(MessageHandler(Filters.forwarded, forwardHandler))#'''处理转发消息'''
    dp.add_handler(MessageHandler(Filters.group&Filters.text, textInGroupHandler))#'''处理群消息'''
    dp.add_handler(MessageHandler(Filters.private&Filters.text, startHandler))#所有private消息当作start处理
    dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, onleft))#'''处理成员离开'''
    dp.add_handler(MessageHandler(documentFilter(),fileHandler))#'''处理文件

    # log all errors
    dp.add_error_handler(error)

    # periodical refresh
    updater.job_queue.run_repeating(refreshAdmins,interval=3600,first=0)
    updater.job_queue.run_repeating(refreshInfos,interval=100,first=0)
    updater.job_queue.run_daily(resetCodebonus,datetime.time())



    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()




if __name__ == '__main__':
    main()
