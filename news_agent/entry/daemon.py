import asyncio
import logging
import signal
import time
from datetime import datetime, timezone

import schedule

from news_agent.core.fetcher import fetch_all_news
from news_agent.core.generator import generate_bulletin_to_file
from news_agent.config.sources import build_topics
from news_agent.infra.utils import setup_logging, DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)

_running = True


def _signal_handler(sig, frame):
    global _running
    _running = False
    logger.info("收到停止信号，正在退出...")


async def _generate_job(days, output_dir, use_hn_api, start_time=None,
                        end_time=None, topics=None, config=None):
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info(f"开始生成 {date_str} 的日刊...")

    try:
        news = fetch_all_news(days=days, use_hn_api=use_hn_api,
                              start_time=start_time, end_time=end_time,
                              topics=topics)
        logger.info(f"获取到 {len(news)} 条相关新闻")

        if not news:
            logger.info("未获取到相关新闻，跳过日刊生成")
            return

        filepath = await generate_bulletin_to_file(
            news_list=news, date_str=date_str, output_dir=output_dir,
            topics=topics, config=config,
        )
        logger.info(f"日刊已生成: {filepath}")
    except Exception as e:
        logger.error(f"日刊生成失败: {e}", exc_info=True)


def _scheduled_job(days, output_dir, use_hn_api, morning_hour=None,
                   topics=None, config=None):
    topics_dict = build_topics(topics)

    now = datetime.now(timezone.utc)
    if morning_hour is not None:
        start_time = datetime(now.year, now.month, now.day - 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(now.year, now.month, now.day, morning_hour, 0, 0, tzinfo=timezone.utc)
    else:
        start_time = None
        end_time = None

    try:
        asyncio.run(_generate_job(days, output_dir, use_hn_api,
                                  start_time=start_time, end_time=end_time,
                                  topics=topics_dict, config=config))
    except Exception as e:
        logger.error(f"定时任务执行异常: {e}", exc_info=True)


def run_daemon(time_str="08:00", days=1, output_dir=None, use_hn_api=False,
               morning_mode=False, topics=None, config=None):
    setup_logging()

    if not output_dir:
        output_dir = DEFAULT_OUTPUT_DIR

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    morning_hour = None
    if morning_mode:
        try:
            morning_hour = int(time_str.split(":")[0])
        except (ValueError, IndexError):
            morning_hour = 6
        logger.info(f"晨报模式：每日 {time_str} 生成昨天0:00至今天{morning_hour:02d}:00的新闻")

    provider = config.get("model_provider", "dashscope") if config else "dashscope"
    model_name = config.get("model_name", "unknown") if config else "unknown"
    logger.info(f"模型配置: {provider}/{model_name}")

    schedule.every().day.at(time_str).do(
        _scheduled_job, days=days, output_dir=output_dir,
        use_hn_api=use_hn_api, morning_hour=morning_hour,
        topics=topics, config=config,
    )

    if not morning_mode:
        logger.info(f"后台守护模式已启动，每日 {time_str} 自动生成日刊")
    logger.info("按 Ctrl+C 停止")
    logger.info("守护期间静默等待，不会消耗AI token")

    while _running:
        schedule.run_pending()
        time.sleep(60)

    logger.info("守护模式已停止")