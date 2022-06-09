import re
import sys
import time
import datetime
import random
import os
import hashlib
from bisect import bisect_right
import json

from mirai.models.api import MessageFromIdResponse
from log import Log
from oj_api import atc_api, cf_api, nc_api, lc_api
from mirai.models import NewFriendRequestEvent, Quote, Group, Friend
from mirai import Startup, Shutdown, MessageEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from mirai_extensions.trigger import HandlerControl, Filter
from mirai import Mirai, WebSocketAdapter, FriendMessage, At, Plain, MessageChain, Image, GroupMessage
from mirai.exceptions import ApiError

sys.stdout = Log.Logger()  # 定义log类
sys.stderr = Log.Logger()
scheduler = AsyncIOScheduler()

cf = cf_api.CF()
nc = nc_api.NC()
lc = lc_api.LC()
atc = atc_api.ATC()

print(cf.info)
print(nc.info)
print(lc.info)
print(atc.info)

img_ruishen = os.listdir('./img/ruishen/')
img_qcjj = os.listdir('./img/qcjj/')


async def sjrs():
    global img_ruishen
    while True:
        if img_ruishen:
            tmp = random.choice(img_ruishen)
            img_local = './img/ruishen/' + tmp
            img_ruishen.remove(tmp)
            return img_local
        else:
            img_ruishen = os.listdir('./img/ruishen/')


async def lzqc():
    global img_qcjj
    while True:
        if img_qcjj:
            tmp = random.choice(img_qcjj)
            img_local = './img/qcjj/' + tmp
            img_qcjj.remove(tmp)
            return img_local
        else:
            img_qcjj = os.listdir('./img/qcjj/')


async def update():
    print()
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    global cf, nc, lc, atc
    await cf.update_contest()
    await nc.update_contest()
    await lc.update_contest()
    await atc.update_contest()


async def query_next_contest():
    global cf, atc, nc, lc
    next_contest = [[cf.info, cf.begin_time], [atc.info, atc.begin_time], [nc.info, nc.begin_time],
                    [lc.info, lc.begin_time]]
    next_contest.sort(key=lambda x: x[1])
    return next_contest


async def query_today_contest():
    next_contest = await query_next_contest()
    res = ""
    mon = datetime.datetime.now().month
    day = datetime.datetime.now().day
    for contest in next_contest:
        if time.localtime(contest[1]).tm_mon == mon and time.localtime(contest[1]).tm_mday == day:
            res += contest[0] + '\n'
    print(res)
    return res.rstrip('\n')


async def sche_add(func, implement):
    scheduler.add_job(func, CronTrigger(month=time.localtime(implement).tm_mon,
                                        day=time.localtime(implement).tm_mday,
                                        hour=time.localtime(implement).tm_hour,
                                        minute=time.localtime(implement).tm_min,
                                        second=time.localtime(implement).tm_sec,
                                        timezone='Asia/Shanghai'), misfire_grace_time=60)


if __name__ == '__main__':
    bot = Mirai(
        qq=1045760198,  # 改成你的机器人的 QQ 号
        adapter=WebSocketAdapter(
            verify_key='yirimirai', host='localhost', port=7275
        )
    )
    hdc = HandlerControl(bot)  # 事件接收器


    @bot.on(Startup)
    def start_scheduler(_):
        scheduler.start()  # 启动定时器


    @bot.on(Shutdown)
    def stop_scheduler(_):
        scheduler.shutdown(True)  # 结束定时器


    @bot.on(NewFriendRequestEvent)
    async def allow_request(event: NewFriendRequestEvent):  # 有新用户好友申请就自动通过
        await bot.allow(event)


    @bot.on(MessageEvent)
    async def show_list(event: MessageEvent):  # 功能列表展示
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg == "help":
            await bot.send(event, ["next -> 最近一场比赛"
                                   "\ncf/牛客/lc/atc -> 最近cf/牛客/lc/atc比赛"
                                   "\ntoday -> 今日比赛"
                                   "\njrrp -> 今日人品"
                                   "\n查询cf/牛客/atc分数id -> 查询对应id的cf/牛客/atc分数"
                                   "\n添加/删除cf用户id -> 添加/删除本群cf用户"
                                   "\ncf总查询 -> 查询本群所有cf用户rating分"
                                   "\n订阅cf/牛客/lc/atc -> 在比赛开始前15分钟发送定时提醒"
                                   "\n订阅每日提醒 -> 每天早上8点提醒当日所有比赛"
                                   "\n取消订阅cf/牛客/lc/atc/每日提醒"
                                   "\n随机/来只蕊神 -> 随机蕊神语录"
                                   "\n来只清楚 -> 随机qcjj语录"
                                   "\nsetu/涩图 -> 涩图"
                                   "\n项目地址 -> 获取项目地址"
                                   "\nbug联系：2454256424"])


    @bot.on(MessageEvent)
    async def on_group_message(event: MessageEvent):  # 返回
        if At(bot.qq) in event.message_chain and len("".join(map(str, event.message_chain[Plain]))) in [0, 1]:
            message_chain = MessageChain([
                await Image.from_local('./img/at_bot.gif')
            ])
            await bot.send(event, message_chain)


    @bot.on(MessageEvent)
    async def project_address(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg == '项目地址':
            await bot.send(event, "大佬可以点个star✨吗qwq\nhttps://github.com/guke1024/ACM_Contest_QQbot")


    @bot.on(MessageEvent)
    async def withdraw_message(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip() == "撤回":
            if event.sender.id == 2454256424:
                quotes = event.message_chain[Quote]
                if quotes:
                    message: MessageFromIdResponse = await bot.message_from_id(quotes[0].id)
                    try:
                        await bot.recall(message.data.message_chain.message_id)
                    except ApiError:
                        await bot.send(event, "撤回失败！")
                        pass


    @bot.on(MessageEvent)
    async def subscribe(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg[:2] == '订阅':
            k = msg[2:].lower()
            if k == '每日提醒':
                k = "today"
            if k in ['cf', '牛客', 'lc', 'atc', 'today']:
                e_type = event.type
                if e_type == 'GroupMessage':
                    id = event.sender.group.id
                else:
                    id = event.sender.id
                id = str(id)
                with open('./oj_json/subscribe.json', 'r+', encoding='utf-8') as f:
                    all_subscribe = json.load(f)
                    if id in all_subscribe[k]:
                        await bot.send(event, "该内容已订阅！")
                    else:
                        all_subscribe[k][id] = e_type
                        f.seek(0)
                        f.truncate()
                        json.dump(all_subscribe, f, indent=4)
                        await bot.send(event, "添加订阅成功！")
            else:
                await bot.send(event, "请输入正确的订阅内容！")


    @bot.on(MessageEvent)
    async def delete_subscribe(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg[:4] == '取消订阅':
            k = msg[4:].lower()
            if k == '每日提醒':
                k = "today"
            if k in ['cf', '牛客', 'lc', 'atc', 'today']:
                with open('./oj_json/subscribe.json', 'r+', encoding='utf-8') as f:
                    all_subscribe = json.load(f)
                    e_type = event.type
                    if e_type == 'GroupMessage':
                        id = event.sender.group.id
                    else:
                        id = event.sender.id
                    id = str(id)
                    if id not in all_subscribe[k]:
                        await bot.send(event, "暂未订阅该内容！")
                    else:
                        del all_subscribe[k][id]
                        f.seek(0)
                        f.truncate()
                        json.dump(all_subscribe, f, indent=4)
                        await bot.send(event, "取消订阅成功！")
            else:
                await bot.send(event, "请输入正确的订阅内容！")


    @bot.on(MessageEvent)
    async def practice_query(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() in ["jrrp", "今日人品"]:
            today_date = time.localtime()
            rp_str = str(event.sender.id) + str(today_date.tm_year) + str(today_date.tm_mon) + str(today_date.tm_mday)
            rp_hash = hashlib.sha256(rp_str.encode('utf-8')).hexdigest()
            rp = int(rp_hash[62:], 16) % 100
            rp_range = [10, 20, 40, 60, 80, 90, 101]
            rp_dict = {0:"大凶", 1:"凶", 2:"末吉", 3:"小吉", 4:"中吉", 5:"吉", 6:"大吉"}
            res = ' 今日人品是{}，为“{}”'.format(rp, rp_dict[bisect_right(rp_range, rp)])
            await bot.send(event, [At(event.sender.id), res])


    @bot.on(MessageEvent)
    async def qcjj_query(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip()[:4] == "来只清楚":
            img_local = await lzqc()
            print(img_local)
            message_chain = MessageChain([
                await Image.from_local(img_local)
            ])
            await bot.send(event, message_chain)


    @bot.on(MessageEvent)
    async def qcjj_query(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip()[:4] in ["随机蕊神", "随机闵神", "来只蕊神"]:
            img_local = await sjrs()
            print(img_local)
            message_chain = MessageChain([
                await Image.from_local(img_local)
            ])
            await bot.send(event, message_chain)


    @bot.on(MessageEvent)
    async def setu_query(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() in ["setu", "涩图"]:
            img_list = os.listdir('./img/setu/')
            img_local = './img/setu/' + random.choice(img_list)
            print(img_local)
            message_chain = MessageChain([
                await Image.from_local(img_local)
            ])
            await bot.send(event, message_chain)


    @bot.on(MessageEvent)
    async def color_query(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip() == "色图":
            message_chain = MessageChain([
                await Image.from_local('./img/color.jpg')
            ])
            await bot.send(event, message_chain)


    @bot.on(MessageEvent)
    async def add_image(event: MessageEvent):
        global img_ruishen
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip() == '添加蕊神':
            if event.sender.id == 2454256424:
                quotes = event.message_chain[Quote]
                message: MessageFromIdResponse = await bot.message_from_id(quotes[0].id)
                images = message.data.message_chain[Image]
                for image in images:
                    all_img_ruishen = os.listdir('./img/ruishen/')
                    suffix = image.image_id.split('.')[1]
                    id_ruishen = str(len(all_img_ruishen) + 1) + '.' + suffix
                    filename_ruishen = './img/ruishen/' + id_ruishen
                    await image.download(filename_ruishen, None, False)
                    img_ruishen.append(id_ruishen)
                    await bot.send(event, '添加成功！')
            else:
                await bot.send(event, "你没有该权限！")


    @bot.on(MessageEvent)
    async def add_image(event: MessageEvent):
        global img_qcjj
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip() == '添加清楚':
            if event.sender.id == 2454256424 or event.sender.group.id in [839594887, 959366007]:
                quotes = event.message_chain[Quote]
                for quote in quotes:
                    message: MessageFromIdResponse = await bot.message_from_id(quote.id)
                    images = message.data.message_chain[Image]
                    for image in images:
                        all_img_qcjj = os.listdir('./img/qcjj/')
                        suffix = image.image_id.split('.')[1]
                        id_qcjj = str(len(all_img_qcjj) + 1) + '.' + suffix
                        filename_qcjj = './img/qcjj/' + id_qcjj
                        await image.download(filename_qcjj, None, False)
                        img_qcjj.append(id_qcjj)
                        await bot.send(event, '添加成功！')
            else:
                await bot.send(event, "本群暂无权限，请联系管理员！")


    @bot.on(MessageEvent)
    async def next_contest(event: MessageEvent):  # 查询近期比赛
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == 'next':
            contest = await query_next_contest()
            if contest[0][1] != 32536799999:
                res = '找到最近的 1 场比赛如下：\n' + contest[0][0]
                await bot.send(event, res)
            else:
                await bot.send(event, '最近没有比赛哦~')


    @bot.on(MessageEvent)
    async def query_today(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == 'today':
            res = await query_today_contest()
            await bot.send(event, "找到今天的比赛如下：\n" + res if res != '' else "今天没有比赛哦~")


    @bot.on(MessageEvent)
    async def update_cf_contest(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == "更新cf比赛":
            global cf
            await bot.send(event, "更新cf比赛成功！" if await cf.update_contest() else "更新cf比赛失败！")


    @bot.on(MessageEvent)
    async def query_cf_contest(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == 'cf':
            global cf
            res = await cf.get_contest_info()
            await bot.send(event, res)


    @bot.on(MessageEvent)
    async def update_all_q(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == "更新cf分数":
            if event.sender.id == 2454256424:
                await bot.send(event, '更新中……')
                res = await cf.update_rating()
                await bot.send(event, res)
            else:
                await bot.send(event, "你没有该权限！")


    @bot.on(MessageEvent)
    async def add_cf_user(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        m = re.match(r'^添加cf用户\s*([\w.,-]+)\s*$', msg.strip(), re.I)
        if m:
            if event.type == "FriendMessage":
                await bot.send(event, "此功能暂时仅支持群聊！")
            else:
                unames = m.group(1).split(',')
                for uname in unames:
                    group_id = str(event.sender.group.id)
                    await bot.send(event, '添加成功！' if await cf.add_cf_user(uname, group_id) else "该用户不存在或cf api异常！")


    @bot.on(MessageEvent)
    async def del_cf_user(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        m = re.match(r'^删除cf用户\s*([\w.,-]+)\s*$', msg.strip(), re.I)
        if m:
            if event.type == "FriendMessage":
                await bot.send(event, "此功能暂时仅支持群聊！")
            else:
                unames = m.group(1).split(',')
                for uname in unames:
                    group_id = str(event.sender.group.id)
                    await bot.send(event, '删除成功！' if await cf.del_cf_user(uname, group_id) else '该用户不存在！')


    @bot.on(MessageEvent)
    async def query_cf_rank(event: MessageEvent):  # 查询对应人的分数
        msg = "".join(map(str, event.message_chain[Plain]))
        m = re.match(r'^查询CF分数\s*([\w.-]+)\s*$', msg.strip(), re.I)
        if m is None:
            m = re.match(r'^查询(.*)的CF分数$', msg.strip(), re.I)
        if m:
            name = m.group(1)
            global cf
            if int(time.time()) - cf.query_time < 3:
                await bot.send(event, '不要频繁查询，请{}秒后再试'.format(int(cf.query_time + 3 - int(time.time()))))
                return
            cf.query_time = time.time()
            statue = await cf.get_rating(name)
            await bot.send(event, statue)


    @bot.on(MessageEvent)
    async def all_q(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == "cf总查询":
            if event.type == "FriendMessage":
                await bot.send(event, "此功能暂时仅支持群聊！")
            else:
                group_id = str(event.sender.group.id)
                res = await cf.get_cf_rating(group_id)
                await bot.send(event, res)


    @bot.on(MessageEvent)
    async def send_all_q(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower()[:6] == "发送cf分数":
            group = msg.strip().lower()[6:]
            group = group if group else '805571983'
            res = await cf.get_cf_rating(group)
            await bot.send_group_message(int(group), "cf分数更新成功！")
            await bot.send_group_message(int(group), res)


    @bot.on(MessageEvent)
    async def rscf(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        m = re.match(r'^cf加([0-9]*)$', msg.strip(), re.I)
        if m:
            if event.sender.id == 2454256424:
                num = int(m.group(1))
                f = open('./cfrs.txt', 'r+', encoding='utf-8')
                number = int(f.read())
                number += num
                f.seek(0)
                f.truncate()
                f.write(str(number))
                f.close()
                await bot.send(event, "更新成功！")
            else:
                await bot.send(event, "你没有该权限！")


    @bot.on(MessageEvent)
    async def query_atc_contest(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == 'atc':
            global atc
            res = await atc.get_contest_info()
            await bot.send(event, res if res else "获取比赛时出错，请联系管理员")


    @bot.on(MessageEvent)
    async def query_atc_rank(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))

        m = re.match(r'^查询ATC分数\s*([\w.-]+)\s*$', msg.strip(), re.I)
        if m is None:
            m = re.match(r'^查询(.*)的ATC分数$', msg.strip(), re.I)

        if m:
            name = m.group(1)
            global atc
            if int(time.time()) - atc.query_time < 5:
                await bot.send(event, '不要频繁查询，请{}秒后再试'.format(int(atc.query_time + 5 - int(time.time()))))
                return
            atc.query_time = time.time()
            statue = await atc.get_rating(name)
            if statue != -1:
                await bot.send(event, statue)
            else:
                await bot.send(event, "不存在这个用户或查询出错哦")


    @bot.on(MessageEvent)
    async def update_nc_contest(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip() == "更新牛客比赛":
            global nc
            await bot.send(event, "更新牛客比赛成功！" if await nc.update_contest() else "更新牛客比赛失败！")


    @bot.on(MessageEvent)
    async def query_nc_contest(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip() == "牛客":
            global nc
            res = await nc.get_contest_info()
            await bot.send(event, res if res else "获取比赛时出错，请联系管理员")


    @bot.on(MessageEvent)
    async def update_nc_rating(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip() == "更新牛客分数" or msg.strip().lower() == "更新牛客rating":
            await bot.send(event, "更新牛客rating成功！" if await nc.update_all_nc_rating() else "更新牛客rating失败！")


    @bot.on(MessageEvent)
    async def query_nc_rating(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        m = re.match(r'^查询牛客分数\s*([\u4e00-\u9fa5\w.-]+)\s*$', msg.strip())
        if m:
            uname = m.group(1)
            rating = await nc.get_rating(uname)
            await bot.send(event, rating if rating else "该用户不存在！")


    @bot.on(MessageEvent)
    async def update_lc_contest(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == "更新lc比赛" or msg.strip().lower() == "更新leetcode比赛":
            global lc
            await bot.send(event, "更新LeetCode比赛成功！" if await lc.update_contest() else "更新LeetCode比赛失败！")


    @bot.on(MessageEvent)
    async def query_lc_contest(event: MessageEvent):
        msg = "".join(map(str, event.message_chain[Plain]))
        if msg.strip().lower() == "lc":
            global lc
            res = await lc.get_contest_info()
            await bot.send(event, res)


    async def note(name, content):
        with open('./oj_json/subscribe.json', 'r', encoding='utf-8') as f:
            all_subscribe = json.load(f)
            for user_id in all_subscribe[name]:
                if all_subscribe[name][user_id] == 'GroupMessage':
                    event = Group(id=user_id, name='', permission='MEMBER')
                else:
                    event = Friend(id=user_id)
                try:
                    await bot.send(event, content)
                except:
                    with open('./oj_json/subscribe.json', 'r+', encoding='utf-8') as f:
                        all_subscribe = json.load(f)
                        del all_subscribe[name][user_id]
                        f.seek(0)
                        f.truncate()
                        json.dump(all_subscribe, f, indent=4)
                    await bot.send_friend_message(2454256424, "{}已成功取消订阅！".format(user_id))


    async def auto_update_cf_user():
        res = await cf.update_rating()
        if res != "更新cf分数失败！":
            await note('cf', 'cf rating更新成功！')
        else:
            await bot.send_friend_message(2454256424, 'cf rating更新失败！')


    async def cf_note():
        global cf
        message_chain = await cf.get_recent_info()
        await note('cf', message_chain)


    async def cf_shang_hao():
        message_chain = MessageChain([
            await Image.from_local('./img/up_cf.jpg')
        ])
        await note('cf', message_chain)


    async def cf_xia_hao():
        message_chain = MessageChain([
            await Image.from_local('./img/down_cf.jpg')
        ])
        await note('cf', message_chain)


    async def nc_note():
        global nc
        message_chain = await nc.get_recent_info()
        await note('牛客', message_chain)


    async def nc_shang_hao():
        message_chain = MessageChain([
            await Image.from_local('./img/up_nc.png')
        ])
        await note('牛客', message_chain)


    async def lc_note():
        global lc
        message_chain = await lc.get_recent_info()
        await note('lc', message_chain)


    async def atc_note():
        global atc
        message_chain = await atc.get_recent_info()
        await note('atc', message_chain)
    

    async def notify_contest_info():
        res = await query_today_contest()
        if res != '':
            msg = "早上好呀~今天的比赛有：\n" + res.strip()
        else:
            msg = "今天没有比赛哦~记得刷题呀！"
        await note('today', msg)


    async def notify_project():
        message_chain = MessageChain([
            At(2837323305),
            At(3073369365),
            At(1351496641),
            At(1821503263),
            At(2232364398),
            At(2948065094),
            Plain(' 项目组请及时回复当日进度')
        ])
        await bot.send_group_message(805571983, message_chain)


    @scheduler.scheduled_job('interval', minutes=30, timezone='Asia/Shanghai')
    async def refresh_job():
        scheduler.remove_all_jobs()
        await update()
        await sche_job()
        msg = 'success：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        await bot.send_group_message(479083059, msg)


    async def sche_job():
        global cf, atc, nc, lc
        await sche_add(update, cf.update_time)
        await sche_add(update, atc.update_time)
        await sche_add(update, nc.update_time)
        await sche_add(update, lc.update_time)
        await sche_add(cf_note, cf.note_time)
        await sche_add(cf_shang_hao, cf.begin_time)
        await sche_add(cf_xia_hao, cf.end_time)
        await sche_add(nc_note, nc.note_time)
        await sche_add(nc_shang_hao, nc.begin_time)
        await sche_add(lc_note, lc.note_time)
        up_time = await cf.auto_update()
        await sche_add(auto_update_cf_user, up_time)
        scheduler.add_job(update, 'interval', hours=9, timezone='Asia/Shanghai', misfire_grace_time=60)
        scheduler.add_job(notify_contest_info, CronTrigger(hour=8, minute=0, timezone='Asia/Shanghai'),
                          misfire_grace_time=60)
        # scheduler.add_job(notify_project, 'cron', hour=21, timezone='Asia/Shanghai', misfire_grace_time=60)
        scheduler.add_job(refresh_job, 'cron', hour=5, minute=0, second=0, timezone='Asia/Shanghai',
                          misfire_grace_time=60)

        # scheduler.add_job(rs, 'cron', hour='0-23', timezone='Asia/Shanghai')


    @Filter(FriendMessage)
    def filter_(event: FriendMessage):  # 定义过滤器，在过滤器中对事件进行过滤和解析
        msg = str(event.message_chain)
        # 如果好友发送的消息格式正确，过滤器返回消息的剩余部分。比如，好友发送“ / command”，过滤器返回'command'。
        # 如果好友发送的消息格式不正确，过滤器隐式地返回None。
        if msg.startswith('/'):
            return msg[1:]


    @hdc.on(filter_)
    async def handler(event: FriendMessage, payload: str):
        global cf
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cf.begin_time)))
        print(time.strftime("%Y-%m-%d %H:%M:%S",
                            time.localtime(cf.end_time)))
        await bot.send(event, f'命令 {payload} 执行成功。')


    bot.run()
