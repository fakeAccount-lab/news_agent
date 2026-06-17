import json
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

import feedparser

from news_agent.config.sources import (
    RSS_SOURCES, BUILTIN_TOPICS, HN_API_URL,
)

logger = logging.getLogger(__name__)


def _classify(title, topics=None):
    if topics is None:
        topics = BUILTIN_TOPICS
    t = title.lower()
    matched = []
    for topic_name, keywords in topics.items():
        if any(kw.lower() in t for kw in keywords):
            matched.append(topic_name)
    if not matched:
        return None
    return ",".join(matched)


def _parse_date(entry):
    for field in ("published_parsed", "updated_parsed"):
        tp = entry.get(field)
        if tp:
            try:
                return datetime(*tp[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError) as e:
                logger.debug(f"日期解析异常 [{field}]: {e}")
    return None


def _extract_image(entry):
    for field in ("media_content", "enclosures"):
        media = entry.get(field, [])
        for m in media:
            url = m.get("url", m.get("href", ""))
            if url and any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")):
                return url

    content = entry.get("summary", entry.get("description", entry.get("content", [{}])))
    if isinstance(content, list):
        content = content[0].get("value", "") if content else ""
    if isinstance(content, str):
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        if m:
            return m.group(1)
    return ""


def _resolve_time_range(days=None, start_time=None, end_time=None):
    if start_time and end_time:
        return start_time, end_time
    if days is None:
        days = 1
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=days), now)


def _fetch_json(url, timeout=10):
    req = Request(url, headers={"User-Agent": "NewsAgent/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError) as e:
        logger.warning(f"网络请求失败 {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败 {url}: {e}")
        return None
    except TimeoutError:
        logger.warning(f"请求超时 {url}")
        return None
    except Exception as e:
        logger.warning(f"未知请求异常 {url}: {e}")
        return None


def _make_article(source, title, url, date, score=0, desc="", image="", category=""):
    return {
        "source": source,
        "title": title,
        "url": url,
        "date": date,
        "score": score,
        "desc": desc,
        "image": image,
        "category": category,
    }


def fetch_hackernews_top(days=1, limit=30, start_time=None, end_time=None, topics=None):
    stories = []
    ids = _fetch_json(f"{HN_API_URL}/topstories.json")
    if not ids:
        logger.warning("Hacker News topstories API 返回空数据")
        return stories

    cutoff, upper = _resolve_time_range(days=days, start_time=start_time, end_time=end_time)
    fetched = 0

    for item_id in ids[:limit * 3]:
        if fetched >= limit:
            break
        item = _fetch_json(f"{HN_API_URL}/item/{item_id}.json")
        if not item:
            continue

        fetched += 1
        title = item.get("title", "")
        cat = _classify(title, topics=topics)
        if not title or cat is None:
            continue

        try:
            created = datetime.fromtimestamp(item["time"], tz=timezone.utc)
        except (TypeError, KeyError, OSError):
            continue
        if created < cutoff or created > upper:
            continue

        stories.append(_make_article(
            source="Hacker News",
            title=title,
            url=item.get("url", f"https://news.ycombinator.com/item?id={item_id}"),
            date=created.strftime("%Y-%m-%d %H:%M UTC"),
            score=item.get("score", 0),
            category=cat,
        ))

    logger.info(f"Hacker News API 获取 {len(stories)} 条新闻")
    return stories


def fetch_rss(days=1, start_time=None, end_time=None, topics=None):
    articles = []
    cutoff, upper = _resolve_time_range(days=days, start_time=start_time, end_time=end_time)

    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
        except Exception as e:
            logger.warning(f"RSS源请求失败 [{src['name']}]: {e}")
            continue

        if feed.bozo and not feed.entries:
            logger.warning(f"RSS源解析失败 [{src['name']}]: {feed.bozo_exception}")
            continue

        if not feed.entries:
            logger.debug(f"RSS源无数据 [{src['name']}]")
            continue

        for entry in feed.entries:
            published = _parse_date(entry)
            if published and (published < cutoff or published > upper):
                continue

            title = entry.get("title", "")
            cat = _classify(title, topics=topics)
            if cat is None and src.get("category") != "mixed":
                src_cat = src.get("category")
                if topics and src_cat in topics:
                    cat = src_cat
            if cat is None:
                continue

            image = _extract_image(entry)
            desc_raw = entry.get("summary", entry.get("description", ""))
            if isinstance(desc_raw, list):
                desc_raw = desc_raw[0].get("value", "") if desc_raw else ""
            desc = re.sub(r"<[^>]+>", "", desc_raw)[:500]

            articles.append(_make_article(
                source=src["name"],
                title=title,
                url=entry.get("link", ""),
                date=(published or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC"),
                desc=desc,
                image=image,
                category=cat,
            ))

    logger.info(f"RSS 获取 {len(articles)} 条新闻")
    return articles


def fetch_all_news(days=1, use_hn_api=False, start_time=None, end_time=None, topics=None):
    all_news = fetch_rss(days=days, start_time=start_time, end_time=end_time, topics=topics)
    if use_hn_api:
        all_news.extend(fetch_hackernews_top(days=days, start_time=start_time, end_time=end_time, topics=topics))

    seen = set()
    unique = []
    for n in all_news:
        key = n["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(n)

    unique.sort(key=lambda x: x.get("score", 0), reverse=True)
    logger.info(f"去重后共 {len(unique)} 条新闻")
    return unique