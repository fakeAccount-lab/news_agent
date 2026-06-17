import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone

from news_agent.core.fetcher import fetch_all_news
from news_agent.core.generator import generate_bulletin_to_file
from news_agent.config.model_factory import load_config
from news_agent.config.sources import TOPIC_LABELS, build_topics
from news_agent.infra.utils import setup_logging, safe_print, DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)


async def run_once(days=1, date_str=None, output_dir=None, use_hn_api=False,
                   start_time=None, end_time=None, topics=None, config=None):
    topics_dict = build_topics(topics)
    label_parts = [TOPIC_LABELS.get(t, t) for t in topics_dict]

    if start_time and end_time:
        safe_print(f"正在获取 {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')} UTC 的{'/'.join(label_parts)}新闻...")
    else:
        safe_print(f"正在获取最近 {days} 天的{'/'.join(label_parts)}新闻...")

    news = fetch_all_news(days=days, use_hn_api=use_hn_api,
                          start_time=start_time, end_time=end_time,
                          topics=topics_dict)
    safe_print(f"获取到 {len(news)} 条相关新闻")

    if not news:
        safe_print("未获取到相关新闻，跳过日刊生成")
        return None

    for n in news[:5]:
        safe_print(f"  [{n['source']}] {n['title']}")

    provider = config.get("model_provider", "dashscope")
    model_name = config.get("model_name", "unknown")
    safe_print(f"正在调用 {provider}/{model_name} 整理日刊...")

    filepath = await generate_bulletin_to_file(
        news_list=news, date_str=date_str, output_dir=output_dir,
        topics=topics_dict, config=config,
    )
    return filepath


def parse_date(date_input):
    try:
        return datetime.strptime(date_input, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(f"无效日期格式: {date_input}, 请使用 YYYY-MM-DD")


def parse_time_str(time_str):
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"无效时间格式: {time_str}, 请使用 HH:MM")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        raise ValueError(f"无效时间格式: {time_str}, 请使用 HH:MM")
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"时间超出范围: {time_str}")
    return hour, minute


def main():
    setup_logging()

    parser = argparse.ArgumentParser(
        description="技术日刊生成器（默认AI与网络安全领域）",
    )
    parser.add_argument("--days", type=int, default=1,
                        help="获取最近N天的新闻（默认1）")
    parser.add_argument("--date", type=str, default=None,
                        help="指定日刊日期，格式 YYYY-MM-DD（默认今天）")
    parser.add_argument("--output", type=str, default=None,
                        help="日刊输出目录（默认 news_agent/output）")
    parser.add_argument("--hn-api", action="store_true", default=False,
                        help="启用Hacker News API获取（较慢但数据更多）")
    parser.add_argument("--topics", type=str, default="ai,security",
                        help="指定新闻领域，逗号分隔（默认 ai,security）")
    parser.add_argument("--config", type=str, default=None,
                        help="模型配置文件路径（默认 news_agent/config/config.json）")
    parser.add_argument("--daemon", action="store_true", default=False,
                        help="以后台守护模式运行（定时生成日刊）")
    parser.add_argument("--morning", action="store_true", default=False,
                        help="晨报模式：获取昨天0:00至今天指定时间之前的新闻")
    parser.add_argument("--time", type=str, default="08:00",
                        help="守护模式每天生成时间/晨报截止时间，格式 HH:MM")

    args = parser.parse_args()

    try:
        date_str = parse_date(args.date) if args.date else None
    except ValueError as e:
        safe_print(str(e))
        sys.exit(1)

    output_dir = args.output or DEFAULT_OUTPUT_DIR
    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    config = load_config(args.config)

    start_time = None
    end_time = None
    if args.morning:
        try:
            hour, minute = parse_time_str(args.time)
        except ValueError as e:
            safe_print(str(e))
            sys.exit(1)
        now = datetime.now(timezone.utc)
        start_time = datetime(now.year, now.month, now.day - 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(now.year, now.month, now.day, hour, minute, 0, tzinfo=timezone.utc)

    if args.daemon:
        from news_agent.entry.daemon import run_daemon
        run_daemon(
            time=args.time, days=args.days, output_dir=output_dir,
            use_hn_api=args.hn_api, morning_mode=args.morning,
            topics=topics, config=config,
        )
    else:
        try:
            filepath = asyncio.run(
                run_once(
                    days=args.days, date_str=date_str, output_dir=output_dir,
                    use_hn_api=args.hn_api, start_time=start_time,
                    end_time=end_time, topics=topics, config=config,
                )
            )
            if filepath:
                safe_print(f"日刊已生成: {filepath}")
        except Exception as e:
            logger.error(f"日刊生成失败: {e}", exc_info=True)
            safe_print(f"日刊生成失败: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()