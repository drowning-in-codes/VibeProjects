"""B站直播日报自动推送系统"""

import argparse
import sys

from src.auth import BiliAuth
from src.collector import LiveCollector
from src.analyzer import LiveAnalyzer
from src.notifier import PushNotifier
from src.storage import Storage
from src.config import load_config


def cmd_login(args):
    config = load_config()
    auth = BiliAuth(config)
    if args.cookie:
        auth.login_by_cookie()
    else:
        auth.login_by_qrcode()
    print("登录成功")


def cmd_watch(args):
    config = load_config()
    storage = Storage()
    if args.action == "list":
        uids = storage.get_watch_list()
        print(f"监控列表 ({len(uids)} 位):")
        for uid in uids:
            print(f"  UID: {uid}")
    elif args.action == "add":
        storage.add_watch(args.uid)
        print(f"已添加: {args.uid}")
    elif args.action == "remove":
        storage.remove_watch(args.uid)
        print(f"已移除: {args.uid}")
    elif args.action == "sync":
        auth = BiliAuth(config)
        collector = LiveCollector(auth)
        followings = collector.get_followings()
        storage.sync_watch_list(followings)
        print(f"已同步 {len(followings)} 位关注用户到监控列表")


def cmd_run(args):
    config = load_config()
    storage = Storage()
    auth = BiliAuth(config)
    collector = LiveCollector(auth)
    analyzer = LiveAnalyzer(config)
    notifier = PushNotifier(config)

    print("开始采集直播数据...")
    lives = collector.collect_live_data(storage.get_watch_list())
    if not lives:
        print("当前无主播在直播")
        return

    print(f"采集到 {len(lives)} 场直播")
    for live in lives:
        danmakus = collector.collect_danmaku(live["room_id"])
        live["wordcloud_path"] = analyzer.generate_wordcloud(live, danmakus)
        if config.get("llm", {}).get("api_key"):
            live["summary"] = analyzer.generate_summary(live, danmakus)
        storage.save_live_record(live, danmakus)

    report = analyzer.generate_report(lives)
    notifier.send(report)
    print("日报已推送")


def cmd_schedule(args):
    from apscheduler.schedulers.blocking import BlockingScheduler
    config = load_config()
    cron = config.get("schedule", {}).get("daily_report_cron", "0 22 * * *")
    scheduler = BlockingScheduler()
    scheduler.add_job(lambda: cmd_run(args), "cron",
                      minute=cron.split()[0], hour=cron.split()[1])
    print(f"定时任务已启动 ({cron})")
    scheduler.start()


def main():
    parser = argparse.ArgumentParser(description="B站直播日报自动推送系统")
    subparsers = parser.add_subparsers(dest="command")

    # login
    p_login = subparsers.add_parser("login", help="登录B站")
    p_login.add_argument("--cookie", action="store_true", help="使用配置文件中的cookie登录")

    # watch
    p_watch = subparsers.add_parser("watch", help="管理监控列表")
    p_watch.add_argument("action", choices=["list", "add", "remove", "sync"])
    p_watch.add_argument("uid", type=int, nargs="?", default=0)

    # run
    subparsers.add_parser("run", help="手动执行一次采集+推送")

    # schedule
    subparsers.add_parser("schedule", help="启动定时任务")

    args = parser.parse_args()
    if args.command == "login":
        cmd_login(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "schedule":
        cmd_schedule(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
