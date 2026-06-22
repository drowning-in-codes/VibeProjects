"""
autoTwit - X/Twitter 自动化发帖系统
主程序入口
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

from src.config import config
from src.storage.database import Database
from src.scheduler.tasks import TaskScheduler
from src.xactions.scraper import TweetScraper
from src.xactions.automator import TwitterAutomator
from src.ai.persona import PersonaDistiller
from src.ai.generator import ContentGenerator
from src.zhihu.client import ZhihuAPIClient, ZhihuChatClient
from src.zhihu.scraper import ZhihuScraper
from src.zhihu.persona import ZhihuPersonaDistiller, DistillerConfig


# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    level=config.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
logger.add(
    config.log_file,
    rotation=config.log_rotation,
    retention=config.log_retention,
    level=config.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
)


async def init_database():
    """初始化数据库"""
    db = Database(config.database_path)
    await db.init_db()
    return db


async def manual_crawl(username: str, count: int = 100):
    """手动爬取指定用户的推文"""
    db = await init_database()
    scraper = TweetScraper(db)

    logger.info(f"开始爬取 @{username} 的推文")
    await scraper.scrape_user(username, count)
    logger.info("爬取完成")


async def manual_analyze(username: str):
    """手动分析用户人格"""
    db = await init_database()
    distiller = PersonaDistiller(db)

    logger.info(f"开始分析 @{username} 的人格特征")
    persona = await distiller.analyze_user(username)

    logger.info(f"分析完成:")
    logger.info(f"  语气: {persona.tone}")
    logger.info(f"  话题: {', '.join(persona.topics)}")
    logger.info(f"  高频词: {', '.join(persona.vocabulary[:10])}")


async def manual_generate(topic: str = None, with_image: str = "auto"):
    """手动生成推文

    Args:
        topic: 话题关键词
        with_image: 图片模式
            - "auto": 自动判断（默认）
            - "yes": 强制生成图片
            - "no": 强制无图
    """
    db = await init_database()
    generator = ContentGenerator(db)

    # 解析图片参数
    image_mode = None
    if with_image == "yes":
        image_mode = True
    elif with_image == "no":
        image_mode = False
    # "auto" 或其他值保持 None（自动判断）

    logger.info(f"开始生成推文（图片模式: {with_image}）")
    content, image_path = await generator.generate_tweet(topic=topic, with_image=image_mode)

    logger.info("生成的推文:")
    print("\n" + "="*50)
    print(content)
    print("="*50)

    if image_path:
        logger.info(f"生成的配图: {image_path}")
        print(f"\n📷 配图路径: {image_path}")
    else:
        print("\n⚠️  未生成配图")
    print()


async def manual_post(content: str, image_path: str = None):
    """手动发布推文（支持附图）"""
    db = await init_database()
    automator = TwitterAutomator(db)

    logger.info("开始发布推文")
    tweet_id = await automator.post_tweet(content, image_path)
    logger.info(f"发布成功，Tweet ID: {tweet_id}")


async def run_scheduler():
    """运行定时任务"""
    db = await init_database()
    scheduler = TaskScheduler(db)

    scheduler.setup_tasks()
    scheduler.start()

    logger.info("定时任务系统已启动，按 Ctrl+C 退出")

    try:
        # 保持程序运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到退出信号")
        scheduler.shutdown()


async def zhihu_search(query: str, limit: int = 50):
    """知乎搜索"""
    db = await init_database()
    access_secret = config.zhihu_access_secret

    if not access_secret:
        print("错误: 未配置知乎 API 凭证，请在 .env 中设置 ZHIHU_ACCESS_SECRET")
        return

    zclient = ZhihuAPIClient(access_secret)
    scraper = ZhihuScraper(db, zclient)

    logger.info(f"开始搜索知乎: '{query}', 数量: {limit}")
    contents = await scraper.search_and_collect(query, limit=limit)

    print(f"\n{'='*60}")
    print(f"知乎搜索结果: '{query}'")
    print(f"{'='*60}")
    print(f"共收集 {len(contents)} 条内容\n")

    # 按作者分组展示
    authors = {}
    for c in contents:
        if c.author_id not in authors:
            authors[c.author_id] = []
        authors[c.author_id].append(c)

    for author_id, items in list(authors.items())[:10]:
        name = items[0].author_name or author_id
        print(f"📝 {name} (@{author_id}) - {len(items)} 条")
        for item in items[:3]:
            title = item.title or "无标题"
            content_preview = item.content[:80].replace('\n', ' ')
            print(f"   [{item.content_type}] {title[:40]} | {content_preview}...")
        print()

    print("💡 数据已保存到数据库，使用 'zhihu distill' 进行人格蒸馏")


async def zhihu_user(user_id: str, limit: int = 50):
    """收集知乎用户内容 → 蒸馏人格 → 生成 SKILL.md"""
    db = await init_database()
    access_secret = config.zhihu_access_secret

    if not access_secret:
        print("错误: 未配置知乎 API 凭证")
        return

    cfg = DistillerConfig(content_limit=limit, analyze_limit=min(limit, 30))
    distiller = ZhihuPersonaDistiller(db)

    print(f"\n{'='*60}")
    print(f"知乎人格蒸馏: {user_id}")
    print(f"{'='*60}")
    print(f"数据量: {limit} 条 | AI: {cfg.ai_provider} | 深度分析: {cfg.deep_analysis}")
    print()

    skill_path = await distiller.distill_and_generate(user_id, cfg)

    if skill_path:
        # 读取生成的 SKILL.md 展示摘要
        content = Path(skill_path).read_text(encoding="utf-8")
        print(f"\n✅ SKILL.md 已生成: {skill_path}")
        print(f"\n📄 预览（前 400 字）:")
        print("-" * 40)
        # 跳过 frontmatter
        body = content.split("---\n", 2)[-1] if content.count("---") >= 2 else content
        print(body[:400])
        print("...")
    else:
        print("⚠️  蒸馏失败，请检查 API 配置或尝试其他用户")


async def zhihu_distill(query: str, limit: int = 50):
    """知乎搜索 → 按作者蒸馏人格 → 生成 SKILL.md"""
    db = await init_database()
    access_secret = config.zhihu_access_secret

    if not access_secret:
        print("错误: 未配置知乎 API 凭证")
        return

    cfg = DistillerConfig(content_limit=limit, analyze_limit=min(limit, 30))
    distiller = ZhihuPersonaDistiller(db)

    print(f"\n{'='*60}")
    print(f"知乎批量蒸馏: '{query}'")
    print(f"{'='*60}")
    print(f"数据量: {limit} 条/作者 | AI: {cfg.ai_provider}")
    print()

    skill_paths = await distiller.distill_from_search(query, cfg)

    if not skill_paths:
        print("⚠️  未提取到足够的人格特征")
        return

    print(f"\n✅ 已生成 {len(skill_paths)} 个 SKILL.md:\n")
    for path in skill_paths:
        print(f"  📄 {path}")

    print(f"\n💡 使用这些 SKILL.md 文件作为 AI 的写作风格参考")
    print(f"   加载方式: 将 SKILL.md 内容作为 system prompt 传给 AI")


async def zhihu_chat(prompt: str, model: str = "fast"):
    """知乎直答对话"""
    access_secret = config.zhihu_access_secret
    if not access_secret:
        print("错误: 未配置知乎 API 凭证")
        return

    chat_model = model or config.zhihu_chat_model
    client = ZhihuChatClient(access_secret, model=chat_model)

    print(f"\n{'='*60}")
    print(f"知乎直答 ({client.MODELS.get(chat_model, chat_model)})")
    print(f"{'='*60}")
    print(f"❓ {prompt}\n")

    if chat_model == "thinking" or chat_model == "zhida-thinking-1p5":
        # thinking 模型：展示推理过程 + 答案
        result = client.ask_with_reasoning(prompt)
        if result:
            if result["reasoning"]:
                print(f"🧠 思考过程:\n{result['reasoning'][:500]}...\n")
            print(f"💬 回答:\n{result['answer']}")
        else:
            print("⚠️  请求失败")
    else:
        answer = client.ask(prompt)
        if answer:
            print(f"💬 {answer}")
        else:
            print("⚠️  请求失败")

    print()


def print_usage():
    """打印使用说明"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║            autoTwit - X/Twitter 自动化系统                    ║
╚══════════════════════════════════════════════════════════════╝

使用方法:

  启动定时任务系统:
    python main.py start

  X/Twitter 操作:
    python main.py crawl <username> [count]        爬取指定用户推文
    python main.py analyze <username>              分析用户人格特征
    python main.py generate [topic] [image_mode]   生成推文
        image_mode: auto(默认)/yes/no
    python main.py post "<content>" [image]        发布推文（可选附图）

  知乎操作:
    python main.py zhihu search <query> [limit]    搜索知乎内容
    python main.py zhihu user <user_id> [limit]    蒸馏用户人格 → SKILL.md
    python main.py zhihu distill <query> [limit]   批量蒸馏 → 多个 SKILL.md
    python main.py zhihu chat <prompt> [model]     知乎直答对话
        model: fast(默认)/thinking/agent

示例:
    python main.py crawl elonmusk 100
    python main.py analyze elonmusk
    python main.py generate "AI技术"              # 自动判断是否配图
    python main.py generate "AI技术" yes          # 强制配图
    python main.py generate "早安" no             # 强制无图
    python main.py post "这是一条测试推文"
    python main.py post "带图推文" ./temp/image.jpg
    python main.py zhihu search "人工智能" 30
    python main.py zhihu user zhang-jia-wei 50
    python main.py zhihu distill "创业" 50
    python main.py zhihu chat "什么是 AI Agent" fast

    # 蒸馏配置示例
    # 在 config.yaml 中配置:
    #   zhihu.chat_model: thinking     # 蒸馏用模型
    #   zhihu.enabled: true
    # 生成的 SKILL.md 保存在 ./skills/ 目录

配置文件:
    config.yaml     - 主配置文件
    .env            - 环境变量（auth_token, API keys）

注意事项:
    1. 首次使用前请配置 .env 文件
    2. 在 config.yaml 中设置目标用户
    3. 知乎功能需要在 .env 中配置 ZHIHU_ACCESS_SECRET
    4. 建议先手动测试各功能后再启动定时任务
""")


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1]

    try:
        if command == "start":
            await run_scheduler()

        elif command == "crawl":
            if len(sys.argv) < 3:
                print("错误: 请指定用户名")
                print("用法: python main.py crawl <username> [count]")
                return
            username = sys.argv[2]
            count = int(sys.argv[3]) if len(sys.argv) > 3 else 100
            await manual_crawl(username, count)

        elif command == "analyze":
            if len(sys.argv) < 3:
                print("错误: 请指定用户名")
                print("用法: python main.py analyze <username>")
                return
            username = sys.argv[2]
            await manual_analyze(username)

        elif command == "generate":
            topic = sys.argv[2] if len(sys.argv) > 2 else None
            image_mode = sys.argv[3] if len(sys.argv) > 3 else "auto"
            await manual_generate(topic, image_mode)

        elif command == "post":
            if len(sys.argv) < 3:
                print("错误: 请指定推文内容")
                print("用法: python main.py post \"<content>\" [image_path]")
                return
            content = sys.argv[2]
            image_path = sys.argv[3] if len(sys.argv) > 3 else None
            await manual_post(content, image_path)

        elif command == "zhihu":
            if len(sys.argv) < 3:
                print("错误: 请指定知乎子命令")
                print("用法:")
                print("  python main.py zhihu search <query> [limit]")
                print("  python main.py zhihu user <user_id> [limit]")
                print("  python main.py zhihu distill <query> [limit]")
                return

            subcommand = sys.argv[2]

            if subcommand == "search":
                if len(sys.argv) < 4:
                    print("错误: 请指定搜索关键词")
                    print("用法: python main.py zhihu search <query> [limit]")
                    return
                query = sys.argv[3]
                limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
                await zhihu_search(query, limit)

            elif subcommand == "user":
                if len(sys.argv) < 4:
                    print("错误: 请指定用户 ID")
                    print("用法: python main.py zhihu user <user_id> [limit]")
                    return
                user_id = sys.argv[3]
                limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
                await zhihu_user(user_id, limit)

            elif subcommand == "distill":
                if len(sys.argv) < 4:
                    print("错误: 请指定搜索关键词")
                    print("用法: python main.py zhihu distill <query> [limit]")
                    return
                query = sys.argv[3]
                limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
                await zhihu_distill(query, limit)

            elif subcommand == "chat":
                if len(sys.argv) < 4:
                    print("错误: 请指定问题")
                    print("用法: python main.py zhihu chat <prompt> [model]")
                    print("模型: fast(快速) / thinking(深度思考) / agent(智能)")
                    return
                prompt = sys.argv[3]
                model = sys.argv[4] if len(sys.argv) > 4 else "fast"
                await zhihu_chat(prompt, model)

            else:
                print(f"未知知乎子命令: {subcommand}")
                print("可用子命令: search, user, distill, chat")

        else:
            print(f"未知命令: {command}")
            print_usage()

    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
