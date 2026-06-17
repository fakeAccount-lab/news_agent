import logging
import os
import re
from datetime import datetime, timezone

from agentscope.agent import Agent, ReActConfig
from agentscope.message import UserMsg

from news_agent.config.model_factory import load_config, create_model_from_config
from news_agent.config.sources import TOPIC_LABELS
from news_agent.infra.utils import safe_print, DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI与网络安全技术日刊 - {date}</title>
<style>
  :root {{
    --primary: #1a1a2e;
    --accent-sec: #e94560;
    --accent-ai: #0f3460;
    --bg: #f5f5f5;
    --card-bg: #ffffff;
    --text: #2d2d2d;
    --text-light: #666;
    --border: #e0e0e0;
    --highlight-bg: #fff8e1;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, 'Segoe UI', 'Noto Sans SC', sans-serif;
    background: var(--bg); color: var(--text);
    max-width: 960px; margin: 0 auto; padding: 20px;
    line-height: 1.7;
  }}
  .header {{
    background: linear-gradient(135deg, var(--primary), #16213e);
    color: #fff; padding: 40px 30px; border-radius: 12px;
    margin-bottom: 30px; text-align: center;
  }}
  .header h1 {{ font-size: 28px; font-weight: 700; }}
  .header .subtitle {{ font-size: 14px; color: #aaa; margin-top: 8px; }}
  .header .date-badge {{
    display: inline-block; margin-top: 12px;
    background: rgba(255,255,255,0.15); padding: 6px 18px;
    border-radius: 20px; font-size: 16px;
  }}
  .section {{
    margin-bottom: 30px;
  }}
  .section-title {{
    font-size: 22px; font-weight: 700; padding: 10px 0;
    margin-bottom: 16px; display: flex; align-items: center; gap: 10px;
  }}
  .section-title .icon {{
    width: 32px; height: 32px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; font-weight: 700;
  }}
  .sec-icon {{ background: var(--accent-sec); color: #fff; }}
  .ai-icon {{ background: var(--accent-ai); color: #fff; }}
  .card {{
    background: var(--card-bg); border-radius: 10px;
    padding: 24px; margin-bottom: 16px;
    border: 1px solid var(--border);
    transition: box-shadow 0.2s;
  }}
  .card:hover {{ box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
  .card.highlight {{ border-left: 4px solid #ff9800; background: var(--highlight-bg); }}
  .card-title {{
    font-size: 17px; font-weight: 600; margin-bottom: 8px;
  }}
  .card-title a {{
    color: var(--text); text-decoration: none;
  }}
  .card-title a:hover {{ color: #1976d2; }}
  .card-meta {{
    font-size: 13px; color: var(--text-light); margin-bottom: 10px;
    display: flex; gap: 16px; align-items: center;
  }}
  .card-meta .source {{
    background: #e3f2fd; color: #1565c0; padding: 2px 8px;
    border-radius: 4px; font-weight: 500;
  }}
  .card-meta .source.sec {{
    background: #fce4ec; color: #c62828;
  }}
  .card-body {{ font-size: 15px; }}
  .card-body p {{ margin-bottom: 8px; }}
  .card-body h4 {{ font-size: 15px; font-weight: 600; margin: 12px 0 6px; }}
  .card-body ul {{ padding-left: 20px; margin-bottom: 8px; }}
  .card-body li {{ margin-bottom: 4px; }}
  .card-body a {{
    color: #1976d2; text-decoration: none;
  }}
  .card-body a:hover {{ text-decoration: underline; }}
  .card-image {{
    margin: 12px 0; border-radius: 8px; overflow: hidden;
  }}
  .card-image img {{
    max-width: 100%; border-radius: 8px;
  }}
  .timeline {{
    background: #f9f9f9; border-radius: 8px;
    padding: 16px; margin: 10px 0;
  }}
  .timeline h5 {{
    font-size: 14px; font-weight: 600; margin-bottom: 8px;
    color: var(--accent-sec);
  }}
  .references {{
    background: #e8f5e9; border-radius: 8px;
    padding: 16px; margin: 10px 0;
  }}
  .references h5 {{
    font-size: 14px; font-weight: 600; margin-bottom: 8px;
    color: #2e7d32;
  }}
  .summary {{
    background: var(--card-bg); border-radius: 10px;
    padding: 24px; border: 1px solid var(--border);
    margin-bottom: 30px;
  }}
  .summary h3 {{
    font-size: 18px; margin-bottom: 10px;
  }}
  .footer {{
    text-align: center; font-size: 13px;
    color: var(--text-light); padding: 20px;
  }}
  .badge {{
    display: inline-block; font-size: 12px;
    padding: 2px 8px; border-radius: 4px;
    font-weight: 500;
  }}
  .badge-focus {{ background: #ff9800; color: #fff; }}
  .badge-watch {{ background: #2196f3; color: #fff; }}
  .badge-general {{ background: #9e9e9e; color: #fff; }}
</style>
</head>
<body>

{content}

</body>
</html>"""

SYSTEM_PROMPT = (
    "你是一位专业的网络安全与AI领域新闻编辑。"
    "你的任务是将收到的新闻原始列表整理成一份精美的HTML日刊。"
    "请严格按照以下要求输出：\n\n"

    "## 输出格式\n"
    "输出纯HTML内容（不含<html><head><body>标签，只输出body内的内容），"
    "使用以下结构：\n\n"

    "### 页面头部\n"
    "一个.header div，包含日刊标题和日期徽章\n\n"

    "### 网络安全板块\n"
    "一个.section div，标题带.sec-icon图标，包含所有网络安全相关新闻的.card div\n\n"

    "### AI板块\n"
    "一个.section div，标题带.ai-icon图标，包含所有AI相关新闻的.card div\n\n"

    "### 今日总结\n"
    "一个.summary div\n\n"

    "### 页脚\n"
    "一个.footer div\n\n"

    "## 新闻分级\n"
    "每条新闻分三个级别，用badge标注：\n"
    "- 重点关注：badge-focus，必须有详细解读\n"
    "- 值得关注：badge-watch，有一句话摘要\n"
    "- 一般动态：badge-general，仅标题+来源\n\n"

    "## 重点关注新闻的深度处理\n"
    "对于\"重点关注\"级别的新闻，必须额外提供：\n\n"

    "1. **事件时间线**：用.timeline div呈现，梳理事件从起因到现状的完整脉络，"
    "不要局限于当天，要追溯事件根源和后续影响。每条时间线条目包含日期和事件描述。\n\n"

    "2. **技术引用**：如果是技术相关事件（漏洞、攻击手法、AI技术突破等），"
    "用.references div提供相关的：\n"
    "- CVE编号（如有）\n"
    "- 相关学术论文链接\n"
    "- 技术教程/分析文章链接\n"
    "- 官方公告链接\n\n"

    "3. **相关信息**：对于非纯技术的重要事件（监管政策、重大融资、行业事故等），"
    "提供行业背景、影响范围、相关方信息等，帮助读者全面了解。\n\n"

    "## 卡片结构\n"
    "每个.card div包含：\n"
    "- .card-title：标题（英文标题保留原文+中文翻译），带原文链接<a href>\n"
    "- .badge：级别徽章\n"
    "- .card-meta：来源标签+日期\n"
    "- 如有图片：.card-image img\n"
    "- .card-body：解读/摘要/深度内容\n\n"

    "## 语言要求\n"
    "- 所有解读、摘要、时间线用中文撰写\n"
    "- 英文新闻标题保留原文，后附中文翻译\n"
    "- 技术术语保留英文原文\n\n"

    "## 重要提醒\n"
    "- 新闻按实际重要程度分级，网络安全板块优先关注漏洞、攻击事件、数据泄露，"
    "AI板块优先关注技术突破、安全风险、重大产品发布\n"
    "- 不要把所有新闻都标记为重点关注\n"
    "- 日刊最后附\"今日总结\"，分别概括网络安全和AI领域的主要趋势\n"
)


def create_agent(config=None):
    if config is None:
        config = load_config()
    model = create_model_from_config(config)
    return Agent(
        name="news_editor",
        system_prompt=SYSTEM_PROMPT,
        model=model,
        react_config=ReActConfig(max_iters=1),
    )


def _format_raw(n, idx):
    text = (
        f"{idx}. [{n['source']}] [{n['category']}] {n['title']}\n"
        f"   链接: {n['url']}\n"
        f"   日期: {n['date']}\n"
    )
    if n.get("desc"):
        text += f"   描述: {n['desc']}\n"
    if n.get("score", 0) > 0:
        text += f"   HN热度: {n['score']}\n"
    if n.get("image"):
        text += f"   图片: {n['image']}\n"
    text += "\n"
    return text


def _build_fallback_html(news_list, date_str, topics):
    topic_labels = {name: TOPIC_LABELS.get(name, name) for name in topics}
    label_parts = [topic_labels[t] for t in topics]
    title = "与".join(label_parts) + "技术日刊"

    body = (
        '<div class="header">'
        f'<h1>{title}</h1>'
        f'<div class="date-badge">{date_str}</div>'
        '</div>'
    )

    for topic_name in topics:
        label = topic_labels[topic_name]
        tn = [n for n in news_list if topic_name in n["category"].split(",")]
        body += f'<div class="section"><div class="section-title">{label}</div>'
        for n in tn:
            body += (
                f'<div class="card">'
                f'<div class="card-title"><a href="{n["url"]}">{n["title"]}</a></div>'
                f'<div class="card-meta"><span class="source">{n["source"]}</span> {n["date"]}</div>'
                f'</div>'
            )
        body += '</div>'

    body += '<div class="footer">AI整理暂不可用，以上为原始新闻列表</div>'
    return HTML_TEMPLATE.format(date=date_str, content=body)


def _extract_body_from_full_html(html_body):
    if "<html" in html_body.lower():
        m = re.search(r"<body[^>]*>(.*?)</body>", html_body, re.S | re.I)
        if m:
            return m.group(1)
    return html_body


async def generate_bulletin(news_list, date_str=None, topics=None, config=None):
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not topics:
        topics = {"security": None, "ai": None}

    topic_labels = {name: TOPIC_LABELS.get(name, name) for name in topics}

    if not news_list:
        label_parts = [topic_labels[t] for t in topics]
        title = "与".join(label_parts) + "技术日刊"
        body = (
            '<div class="header">'
            f'<h1>{title}</h1>'
            f'<div class="date-badge">{date_str}</div>'
            '</div>'
            '<p>今日未获取到相关新闻。</p>'
        )
        return HTML_TEMPLATE.format(date=date_str, content=body)

    def topic_news(topic_name):
        return [n for n in news_list if topic_name in n["category"].split(",")]

    news_text = ""
    for topic_name in topics:
        label = topic_labels[topic_name]
        tn = topic_news(topic_name)
        news_text += f"\n== {label}板块新闻 ==\n"
        for i, n in enumerate(tn, 1):
            news_text += _format_raw(n, i)

    label_parts = [topic_labels[t] for t in topics]
    title = "与".join(label_parts) + "技术日刊"

    section_desc = ""
    for topic_name in topics:
        label = topic_labels[topic_name]
        section_desc += f"- {label}板块：包含所有{label}相关新闻的.card div\n"

    prompt = (
        f"以下是 {date_str} 获取到的{title}新闻原始列表，"
        f"请将其整理为HTML日刊格式（只输出body内的HTML内容）：\n\n{news_text}\n\n"
        f"## 输出格式要求\n"
        f"输出纯HTML内容（不含<html><head><body>标签，只输出body内的内容），使用以下结构：\n\n"
        f"### 页面头部\n"
        f"一个.header div，包含日刊标题「{title}」和日期徽章\n\n"
        f"### 各板块\n"
        f"{section_desc}\n"
        f"每个板块用一个.section div，标题带对应图标\n\n"
        f"### 今日总结\n"
        f"一个.summary div\n\n"
        f"### 页脚\n"
        f"一个.footer div\n\n"
    )

    agent = create_agent(config)
    user_msg = UserMsg(name="user", content=prompt)

    try:
        response = await agent.reply(user_msg)
        html_body = response.get_text_content()
        html_body = _extract_body_from_full_html(html_body)
    except Exception as e:
        logger.error(f"模型调用失败，使用回退HTML生成: {e}")
        return _build_fallback_html(news_list, date_str, topics)

    return HTML_TEMPLATE.format(date=date_str, content=html_body)


async def generate_bulletin_to_file(news_list, date_str=None, output_dir=None, topics=None, config=None):
    if not output_dir:
        output_dir = DEFAULT_OUTPUT_DIR
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"无法创建输出目录 {output_dir}: {e}")
        raise

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    html = await generate_bulletin(news_list, date_str, topics=topics, config=config)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"daily_{timestamp}.html"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
    except OSError as e:
        logger.error(f"无法写入日刊文件 {filepath}: {e}")
        raise

    safe_print(f"日刊已生成: {filepath}")
    return filepath