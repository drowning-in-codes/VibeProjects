#!/usr/bin/env python3
"""
EasyTwit — 基于 xdk 的 X/Twitter 自动发帖应用

用法:
    python -m src.main scrape              # 爬取目标用户的推文
    python -m src.main distill             # 从推文蒸馏人格
    python -m src.main persona-custom      # 从 config.yaml 创建自定义人格
    python -m src.main generate            # 生成一条推文（预览，不发布）
    python -m src.main post                # 生成并发布一条推文
    python -m src.main post --topic "AI"   # 指定话题发布
    python -m src.main run                 # 启动定时调度器
    python -m src.main status              # 查看状态
    python -m src.main setup               # 初始化数据库和目录
"""
import asyncio
import sys
import argparse
from pathlib import Path

from loguru import logger

from .config import config
from .storage.database import Database
from .x.client import XClient
from .x.scraper import TweetScraper
from .x.auth import oauth_flow
from .ai.persona import PersonaManager
from .ai.generator import ContentGenerator
from .poster import Poster
from .scheduler import Scheduler


# ── 日志配置 ──────────────────────────────────────────────

def setup_logging():
    """配置日志输出到文件和控制台"""
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<level>{message}</level>"
    )

    # 控制台
    logger.add(
        sys.stderr,
        format=log_format,
        level=config.log_level,
        colorize=True,
    )

    # 文件
    log_dir = Path(config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        config.log_file,
        format=log_format,
        level="DEBUG",
        rotation=config.log_rotation,
        retention=config.log_retention,
        encoding="utf-8",
    )


# ── 命令实现 ──────────────────────────────────────────────

async def cmd_auth(port: int = 8000):
    """OAuth 1.0a 认证：获取 access_token 并写入 .env"""
    await oauth_flow(port=port)


async def cmd_trends(woeid: str = "1", count: int = 20, personalized: bool = False):
    """查看趋势"""
    x = XClient()
    if not x.ready:
        logger.error("X 客户端未就绪")
        return

    if personalized:
        trends = x.personalized_trends()
        print(f"\n{'='*50}")
        print("📈 个性化趋势")
    else:
        # 支持名称或数字
        woeid_int = x.WOEID.get(woeid.lower(), None)
        if woeid_int is None:
            try:
                woeid_int = int(woeid)
            except ValueError:
                logger.error(f"无效的 WOEID: {woeid}")
                return
        trends = x.trends(woeid=woeid_int, max_trends=count)
        print(f"\n{'='*50}")
        print(f"📈 趋势 (WOEID: {woeid})")

    print(f"{'='*50}\n")
    if not trends:
        print("  无趋势数据")
        return
    for i, t in enumerate(trends, 1):
        name = t.get('trend_name', t.get('name', '?'))
        volume = t.get('tweet_volume', t.get('volume', '?'))
        category = t.get('category', '')
        print(f"  {i:2}. {name}")
        if volume and volume != '?':
            print(f"      推文量: {volume}")
        if category:
            print(f"      分类: {category}")
    print()


async def cmd_analytics(days: int = 30):
    """数据看板"""
    db = Database()
    await db.initialize()
    x = XClient()

    # 1. 更新指标
    logger.info("正在拉取最新数据...")
    posts = await db.get_posts_without_metrics(limit=config.metrics_fetch_limit)
    updated = 0
    for post in posts[:config.metrics_fetch_limit]:
        if not post.tweet_id:
            continue
        metrics = x.get_tweet_metrics(post.tweet_id)
        if metrics:
            await db.update_post_metrics(post.tweet_id, metrics)
            updated += 1
        await asyncio.sleep(1)  # 速率限制
    logger.info(f"  更新了 {updated}/{len(posts)} 条推文的数据")

    # 2. 汇总展示
    summary = await db.get_analytics_summary(days=days)
    print(f"\n{'='*50}")
    print(f"📊 EasyTwit 数据看板 (最近 {days} 天)")
    print(f"{'='*50}")
    print(f"  发帖数:       {summary.get('total_posts', 0)}")
    print(f"  总曝光:       {summary.get('total_impressions', 0):,}")
    print(f"  总点赞:       {summary.get('total_likes', 0)}")
    print(f"  总转推:       {summary.get('total_retweets', 0)}")
    print(f"  总回复:       {summary.get('total_replies', 0)}")
    posts_count = summary.get('total_posts', 1) or 1
    print(f"  均曝光/帖:    {summary.get('total_impressions', 0) / posts_count:,.0f}")
    print(f"  互动率:       {(summary.get('total_likes', 0) + summary.get('total_retweets', 0)) / max(posts_count, 1):.1%}")

    # 3. 进度
    impressions = summary.get('total_impressions', 0)
    target = 5_000_000
    pct = min(100, impressions / target * 100)
    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
    print(f"\n🎯 500万曝光目标 ({days}/90 天)")
    print(f"   [{bar}] {pct:.1f}% ({impressions:,}/{target:,})")
    print(f"   日均曝光: {impressions / max(days, 1):,.0f} (需要 {target / 90:,.0f})")
    print()


async def cmd_engage():
    """互动增长: 发现 Blue 用户 → like + repost"""
    db = Database()
    await db.initialize()
    x = XClient()
    if not x.ready:
        logger.error("X 客户端未就绪")
        return

    limit = config.get('scheduler.engage_limit', 5)
    logger.info(f"开始互动增长 (上限: {limit})")

    # 搜索 Blue/ 互关相关推文
    queries = ["blue 互关", "X Premium 互关", "蓝标 互关"]
    interacted = 0

    for q in queries:
        if interacted >= limit:
            break
        posts = x.find_blue_users(q, count=min(5, limit - interacted))
        for post in posts[:min(3, limit - interacted)]:
            tid = post.get('id', '')
            if not tid:
                continue
            result = x.interact_with_tweet(tid, like=True, repost=False)
            if result.get('liked') or result.get('reposted'):
                interacted += 1
                logger.info(f"  互动: {tid[:15]}... (query: {q})")
            await asyncio.sleep(2)  # 速率限制

    # 保存
    post = PostHistory(
        content=f"[ENGAGE] 互动了 {interacted} 条推文",
        posted_at=datetime.now(),
        status="success" if interacted > 0 else "pending",
    )
    await db.save_post(post)
    logger.success(f"互动完成: {interacted} 次")


async def cmd_setup():
    """初始化项目"""
    logger.info("EasyTwit 初始化...")

    # 创建必要目录
    dirs = [
        "./data",
        "./data/images",
        "./data/tweets",
        "./logs",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        logger.info(f"  目录: {d}")

    # 初始化数据库
    db = Database()
    await db.initialize()

    # X 客户端检查
    x = XClient()
    if x.ready:
        logger.success("OAuth 1.0a 就绪 (发帖/搜索/用户操作)")
        who = x.whoami()
        if who:
            logger.info(f"  用户: @{who.get('username', '?')}")
    if x._bearer:
        logger.success("Bearer Token 就绪 (趋势/公开接口)")
    if x._oauth2:
        logger.success("OAuth 2.0 就绪 (PKCE)")
    if not x.ready and not x._bearer:
        logger.warning("X 客户端未配置")

    logger.success("初始化完成!")
    logger.info("下一步:")
    logger.info("  1. 编辑 config.yaml — 配置目标用户")
    logger.info("  2. python -m src.main scrape  — 爬取推文")
    logger.info("  3. python -m src.main distill — 蒸馏人格")
    logger.info("  4. python -m src.main run     — 启动自动发帖")


async def cmd_scrape(username: str = None, user_id: str = None, limit: int = 5,
                     following: bool = False, timeline: bool = False):
    """爬取推文

    来源: --username/--id > --following > --timeline > config.yaml
    """
    db = Database()
    await db.initialize()
    scraper = TweetScraper(db)

    if following:
        await scraper.scrape_following(limit)
        return
    if timeline:
        await scraper.scrape_timeline(count=limit)
        return

    # 确定爬取目标用户名
    if username:
        users = [username.lstrip('@')]
    elif user_id:
        x = XClient()
        if not x.ready:
            logger.error("X 客户端未就绪")
            return
        # 通过 ID 查用户名
        user = x.user_info(user_id)
        if not user:
            logger.error(f"未找到用户 ID: {user_id}")
            return
        users = [user.get('username', user_id)]
        logger.info(f"ID → @{users[0]}")
    else:
        users = config.target_users
        if not users:
            logger.error("未指定用户。请使用 --username / --id 或在 config.yaml 中配置 targets.users")
            return

    logger.info(f"开始爬取 {len(users)} 个用户: {', '.join(users)}")
    await scraper.scrape_users(users, limit)

    # 统计
    for user in users:
        count = await db.get_tweet_count(username=user)
        logger.info(f"  @{user}: {count} 条推文")


async def cmd_distill():
    """从推文蒸馏人格"""
    db = Database()
    await db.initialize()

    pm = PersonaManager(db)

    # 先尝试从目标用户蒸馏
    users = config.target_users
    if users:
        for username in users:
            try:
                persona = await pm.distill_from_tweets(username)
                logger.success(
                    f"人格蒸馏完成: @{username}\n"
                    f"  语气: {persona.tone}\n"
                    f"  话题: {', '.join(persona.topics)}\n"
                    f"  高频词: {', '.join(persona.vocabulary[:10])}"
                )
            except ValueError as e:
                logger.error(f"蒸馏失败 @{username}: {e}")

    # 如果有自定义人格配置，也生成
    custom = await pm.create_persona_from_config()
    if custom:
        logger.success(f"自定义人格已创建: {custom.tone}")


async def cmd_persona_custom(use_config: bool = False):
    """交互式创建自定义人格（或从 config.yaml 读取）"""
    db = Database()
    await db.initialize()

    pm = PersonaManager(db)

    if use_config:
        # 从 personas/ 模板加载
        from .config import config as cfg
        tmpl = cfg.persona_template
        if not tmpl:
            logger.error("未配置人格模板 (config.yaml targets.persona_template 为空)")
            return
        persona = await pm.create_persona_from_config()
        if persona:
            logger.success(f"从模板 '{tmpl}' 创建人格: {persona.tone}")
        else:
            logger.error(f"模板加载失败: personas/{tmpl}.yaml")
        return

    # 交互式输入
    print(f"\n{'='*50}")
    print("🧠 创建自定义 AI 人格")
    print(f"{'='*50}\n")

    name = input("人格名称 (如: 技术博主): ").strip()
    if not name:
        logger.error("名称不能为空")
        return

    description = input("具体描述 (如: 一个关注AI和技术前沿的理性思考者): ").strip()
    if not description:
        logger.error("描述不能为空")
        return

    keywords_str = input("关键词 (逗号分隔, 如: AI, 开源, 编程, 创业): ").strip()
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

    tone = input("语气风格 (如: 专业/幽默/理性/毒舌, 回车跳过): ").strip()

    topics_str = input("关注话题 (逗号分隔, 如: 人工智能, 科技趋势, 产品思考, 回车跳过): ").strip()
    topics = [t.strip() for t in topics_str.split(",") if t.strip()] if topics_str else None

    print(f"\n{'='*50}")
    print("正在使用 AI 生成人格...")
    print(f"{'='*50}\n")

    persona = await pm.create_custom_persona(
        name=name,
        description=description,
        keywords=keywords if keywords else ["AI", "科技"],
        tone=tone,
        topics=topics,
    )

    logger.success(
        f"人格已创建:\n"
        f"  名称: {name}\n"
        f"  语气: {persona.tone}\n"
        f"  话题: {', '.join(persona.topics)}\n"
        f"  高频词: {', '.join(persona.vocabulary[:10])}"
    )


async def cmd_generate(topic: str = None):
    """生成推文预览（不发布）"""
    db = Database()
    await db.initialize()

    poster = Poster(db)

    ref_count = config.reference_tweet_count
    ref_tweets = await db.get_all_tweets(limit=ref_count) if ref_count > 0 else None
    result = await poster.post_now(topic=topic, dry_run=True,
                                   reference_tweets=ref_tweets)
    if result:
        print(f"\n{'='*50}")
        print(f"预览推文 ({len(result.content)} 字符):")
        print(f"{'='*50}")
        print(result.content)
        if result.image_path:
            print(f"\n配图: {result.image_path}")
        print(f"{'='*50}")
    else:
        logger.error("生成失败（可能已达每日限额或无可用人格）")


async def cmd_post(topic: str = None, with_image: bool = None):
    """生成并发布推文"""
    db = Database()
    await db.initialize()

    poster = Poster(db)

    print(f"\n{'='*50}")
    print("准备发布推文到 X...")
    print(f"{'='*50}")

    result = await poster.post_now(topic=topic, with_image=with_image)
    if result and result.status == "success":
        print(f"\n✓ 发布成功!")
        print(f"  推文 ID: {result.tweet_id}")
        print(f"  内容: {result.content}")
        if result.image_path:
            print(f"  配图: {result.image_path}")
    elif result and result.status == "failed":
        print(f"\n✗ 发布失败: {result.error_message}")
    else:
        print("\n✗ 发布失败")


async def cmd_pipeline():
    """完整流程: 爬取 → 蒸馏 → 发帖"""
    import time
    from datetime import datetime

    start_time = time.time()
    logger.info("=" * 60)
    logger.info(f"Pipeline 开始 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    db = Database()
    await db.initialize()
    scraper = TweetScraper(db)
    pm = PersonaManager(db)
    poster = Poster(db)

    # ── Step 1: 爬取 ────────────────────────────────────
    t1 = time.time()
    source = config.scrape_source
    user_list = config.target_users
    logger.info(f"[1/3] 爬取推文 | 来源: {source} | 目标: {user_list or '自动检测'}")
    tweets_collected = 0

    scrape_limit = config.get('scheduler.scrape_limit', 5)
    following_limit = config.get('scheduler.following_limit', 5)

    if source == "following":
        tweets = await scraper.scrape_following(following_limit)
        tweets_collected = len(tweets)
    elif source == "timeline":
        tweets = await scraper.scrape_timeline(count=scrape_limit)
        tweets_collected = len(tweets)
    else:
        if user_list:
            tweets = await scraper.scrape_users(user_list, limit_per_user=scrape_limit)
            tweets_collected = len(tweets)
        else:
            logger.warning("  未配置目标用户，fallback → 关注列表")
            tweets = await scraper.scrape_following(following_limit=following_limit, limit_per_user=scrape_limit)
            tweets_collected = len(tweets)

    logger.info(f"  ✓ 爬取完成: {tweets_collected} 条推文 ({time.time() - t1:.1f}s)")

    # ── Step 2: 蒸馏 ────────────────────────────────────
    t2 = time.time()
    logger.info(f"[2/3] 蒸馏人格 | 目标用户: {user_list or '所有已爬取'}")
    persona_count = 0

    target_users = user_list or [t.username for t in (tweets or []) if t.username][:5]
    for username in target_users:
        try:
            await pm.distill_from_tweets(username)
            persona_count += 1
            logger.info(f"  ✓ @{username} 蒸馏成功")
        except ValueError as e:
            logger.warning(f"  ✗ @{username}: {e}")

    if persona_count == 0:
        # 自定义人格 fallback
        custom = await pm.create_persona_from_config()
        if custom:
            persona_count = 1
            logger.info(f"  使用自定义人格: {custom.tone[:40]}...")

    logger.info(f"  ✓ 蒸馏完成: {persona_count} 个人格 ({time.time() - t2:.1f}s)")

    # ── Step 3: 发帖 ────────────────────────────────────
    t3 = time.time()
    posts_today = await db.get_posts_today()
    logger.info(f"[3/3] 发帖 | 今日已发: {posts_today}/{config.max_posts_per_day}")

    result = await poster.post_now()
    if result and result.status == "success":
        elapsed = time.time() - start_time
        logger.success(
            f"  ✓ 发帖成功 | ID: {result.tweet_id} | "
            f"内容长度: {len(result.content)} 字符"
        )
        logger.info(f"Pipeline 完成! 总耗时 {elapsed:.1f}s")
    elif result and result.status == "dry_run":
        logger.info(f"  ⊘ 预览模式 (dry run)")
    else:
        logger.warning(f"  ⊘ 发帖跳过 (已达限额 {config.max_posts_per_day}/天 或 失败)")


async def cmd_easy():
    """轻量模式: 随机人格 → 生成 → 发帖 (跳过爬取蒸馏)"""
    import time
    from datetime import datetime

    start = time.time()
    logger.info("=" * 50)
    logger.info(f"Easy 模式 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    db = Database()
    await db.initialize()
    pm = PersonaManager(db)
    poster = Poster(db)

    # Step 1: 随机人格
    logger.info("[1/2] 加载人格...")
    persona = await pm.create_persona_from_template()
    if not persona:
        persona = await db.get_latest_persona()
    if not persona:
        logger.error("无可用人格")
        return
    logger.info(f"  人格: @{persona.username} — {persona.tone[:40]}...")

    # 加载参考推文
    ref_count = config.reference_tweet_count
    ref_tweets = await db.get_all_tweets(limit=ref_count) if ref_count > 0 else None

    # Step 2: 发帖
    logger.info(f"[2/2] 发帖 | 今日已发: {await db.get_posts_today()}/{config.max_posts_per_day}")
    if ref_tweets:
        logger.info(f"  参考推文: {len(ref_tweets)} 条")
    result = await poster.post(persona=persona, reference_tweets=ref_tweets)
    if result and result.status == "success":
        logger.success(f"Easy 发帖成功 | ID: {result.tweet_id} | {time.time()-start:.1f}s")
    else:
        logger.warning("发帖跳过 (达限额或失败)")


async def cmd_refollow():
    """Follow back followers that are not already followed."""
    limit = config.refollow_limit
    if limit <= 0:
        logger.info("Refollow skipped: scheduler.refollow_limit is 0")
        return

    client = XClient()
    if not client.ready:
        logger.warning("Refollow skipped: X OAuth 1.0a is not configured")
        return

    me = client.whoami() or {}
    own_id = str(me.get('id', ''))
    followers = client.followers(count=None, strict=True)
    following = client.following(count=None, strict=True)
    following_ids = {str(user.get('id')) for user in following if user.get('id')}
    candidates = [
        user for user in followers
        if user.get('id')
        and str(user.get('id')) != own_id
        and str(user.get('id')) not in following_ids
    ][:limit]

    followed = 0
    failed = 0
    for user in candidates:
        if client.follow(str(user['id'])):
            followed += 1
            following_ids.add(str(user['id']))
        else:
            failed += 1
    logger.info(
        f"Refollow complete: followers={len(followers)}, candidates={len(candidates)}, "
        f"followed={followed}, failed={failed}"
    )


async def cmd_run(cron: str = None, now: bool = False, easy: bool = False):
    """启动定时调度 (支持双任务: 发帖 + 定期蒸馏)"""
    db = Database()
    await db.initialize()

    scheduler = Scheduler()
    post_cron = cron or config.post_cron
    distill_cron = config.distill_cron

    # ── 任务 1: 发帖 ──
    if easy:
        async def post_task():
            await cmd_easy()
        post_name = "easy (随机人格→发帖)"
        async def refollow_task():
            await cmd_refollow()
        scheduler.add_task(
            name="refollow (回关粉丝)",
            cron_expr=config.refollow_cron,
            callback=refollow_task,
        )
    else:
        async def post_task():
            await cmd_pipeline()
        post_name = "pipeline (爬取→蒸馏→发帖)"

    scheduler.add_task(name=post_name, cron_expr=post_cron, callback=post_task,
                       jitter_minutes=config.jitter_minutes)

    # ── 任务 2: 定期蒸馏 (复用 cmd_pipeline) ──
    if distill_cron:
        async def distill_task():
            await cmd_pipeline()
        scheduler.add_task(name="distill (定期蒸馏)", cron_expr=distill_cron,
                          callback=distill_task)

    logger.info("=" * 50)
    logger.info("EasyTwit 定时调度已启动")
    logger.info(f"  发帖:   {post_name} @ {post_cron}")
    if distill_cron:
        logger.info(f"  蒸馏:   distill (定期蒸馏) @ {distill_cron}")
    logger.info(f"  上限:   {config.max_posts_per_day} 条/天")
    logger.info(f"  下次:   {scheduler.list_tasks()}")
    logger.info("按 Ctrl+C 停止")
    logger.info("=" * 50)

    # 首次立即执行发帖
    if now or config.run_immediately:
        logger.info(f">>> 启动测试: {post_name}...")
        try:
            await post_task()
            logger.info(">>> 测试完成，进入定时调度")
        except Exception as e:
            msg = str(e)
            if "403" in msg or "401" in msg:
                logger.error(f"🛑 致命错误, 退出: {msg[:200]}")
                return
            logger.warning(f"⚠️ 测试失败, 继续调度: {msg[:150]}")

    try:
        await scheduler.start()
    except KeyboardInterrupt:
        scheduler.stop()
        logger.info("已停止")


async def cmd_status():
    """显示应用状态"""
    db = Database()
    await db.initialize()

    print(f"\n{'='*50}")
    print("EasyTwit 状态")
    print(f"{'='*50}")

    # 推文数量
    total_tweets = await db.get_tweet_count()
    print(f"\n[DB] 已爬取推文: {total_tweets} 条")

    # 人格
    personas = await db.get_all_personas()
    print(f"\n[AI] 人格数据: {len(personas)} 个")
    for p in personas:
        print(f"  @{p.username}: {p.tone} (来源: {p.source})")

    # 今日发布
    posts_today = await db.get_posts_today()
    print(f"\n[POST] 今日发布: {posts_today}/{config.max_posts_per_day} 条")

    # 最近发布
    recent = await db.get_recent_posts(limit=5)
    if recent:
        print(f"\n[HISTORY] 最近发布:")
        for r in recent:
            if r.status == "success":
                status_icon = "OK"
            elif r.status == "dry_run":
                status_icon = "PREVIEW"
            else:
                status_icon = "FAIL"
            print(f"  [{status_icon}] {r.content[:60]}...")

    # 目标用户
    users = config.target_users
    if users:
        print(f"\n[TARGET] 目标用户: {', '.join(users)}")
    else:
        print(f"\n[TARGET] 目标用户: (无，使用自定义人格)")

    print(f"\n[CRON] 调度: {config.post_cron}")
    print()


# ── CLI ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EasyTwit — xdk-based auto-tweet application",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # auth
    auth_parser = subparsers.add_parser("auth", help="OAuth 1.0a 认证流程")
    auth_parser.add_argument("--port", "-p", type=int, default=8000, help="回调端口 (默认8000)")

    # setup
    subparsers.add_parser("setup", help="初始化数据库和目录")

    # scrape
    sc_parser = subparsers.add_parser("scrape", help="爬取推文")
    sc_parser.add_argument("--username", "-u", type=str, help="X 用户名")
    sc_parser.add_argument("--id", "-i", type=str, help="X 用户 ID")
    sc_parser.add_argument("--limit", "-n", type=int, default=100, help="最大爬取数")
    sc_parser.add_argument("--following", "-f", action="store_true",
                           help="爬取关注列表中的用户")
    sc_parser.add_argument("--timeline", "-t", action="store_true",
                           help="爬取时间线上的推文")

    # pipeline
    subparsers.add_parser("pipeline", help="完整流程: 爬取→蒸馏→发帖")

    # distill
    subparsers.add_parser("distill", help="从推文蒸馏人格")

    # persona-custom
    pc_parser = subparsers.add_parser("persona-custom", help="创建自定义人格")
    pc_parser.add_argument("--config", action="store_true",
                           help="从 config.yaml 读取（默认交互式输入）")

    # generate
    gen_parser = subparsers.add_parser("generate", help="生成推文预览")
    gen_parser.add_argument("--topic", "-t", type=str, help="话题关键词")

    # post
    post_parser = subparsers.add_parser("post", help="生成并发布推文")
    post_parser.add_argument("--topic", "-t", type=str, help="话题关键词")
    post_parser.add_argument("--with-image", action="store_true", default=None,
                            help="强制配图")
    post_parser.add_argument("--no-image", action="store_false", dest="with_image",
                            help="强制无图")

    # run
    run_parser = subparsers.add_parser("run", help="启动定时调度器")
    run_parser.add_argument("--now", action="store_true",
                            help="启动后立即执行一次")
    run_parser.add_argument("--cron", "-c", type=str,
                            help="临时 cron 表达式 (测试用, 如 */5 * * * *)")
    run_parser.add_argument("--easy", "-e", action="store_true",
                            help="轻量模式: 跳过爬取蒸馏, 直接随机人格→发帖")

    # trends
    tr_parser = subparsers.add_parser("trends", help="查看趋势")
    tr_parser.add_argument("--woeid", "-w", type=str, default="1",
                           help="WOEID 或地区名 (worldwide/us/uk/japan/korea/canada)")
    tr_parser.add_argument("--count", "-n", type=int, default=20, help="返回数量")
    tr_parser.add_argument("--personalized", "-p", action="store_true",
                           help="个性趋势（基于认证用户）")

    # engage
    subparsers.add_parser("engage", help="互动增长 (like Blue 用户帖子)")

    # analytics
    an_parser = subparsers.add_parser("analytics", help="数据看板")
    an_parser.add_argument("--days", "-d", type=int, default=30, help="统计天数")

    # status
    subparsers.add_parser("status", help="查看应用状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    setup_logging()

    # 路由到对应命令
    commands = {
        "auth": lambda: cmd_auth(port=getattr(args, 'port', 8000)),
        "setup": cmd_setup,
        "pipeline": cmd_pipeline,
        "scrape": lambda: cmd_scrape(
            username=getattr(args, 'username', None),
            user_id=getattr(args, 'id', None),
            limit=getattr(args, 'limit', 100),
            following=getattr(args, 'following', False),
            timeline=getattr(args, 'timeline', False)),
        "distill": cmd_distill,
        "persona-custom": lambda: cmd_persona_custom(
            use_config=getattr(args, 'config', False)),
        "generate": lambda: cmd_generate(topic=getattr(args, 'topic', None)),
        "post": lambda: cmd_post(
            topic=getattr(args, 'topic', None),
            with_image=getattr(args, 'with_image', None),
        ),
        "trends": lambda: cmd_trends(
            woeid=getattr(args, 'woeid', '1'),
            count=getattr(args, 'count', 20),
            personalized=getattr(args, 'personalized', False)),
        "run": lambda: cmd_run(
            cron=getattr(args, 'cron', None),
            now=getattr(args, 'now', False),
            easy=getattr(args, 'easy', False)),
        "engage": cmd_engage,
        "analytics": lambda: cmd_analytics(
            days=getattr(args, 'days', 30)),
        "status": cmd_status,
    }

    func = commands.get(args.command)
    if func:
        asyncio.run(func())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
