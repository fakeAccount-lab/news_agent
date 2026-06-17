# News Agent 从 0 到 1 开发教学

> 本文档是一份完整的开发教学，旨在让读者在学习完成后能够独立从零开发出 news-agent 项目——一个基于 AgentScope 的自动化技术新闻日刊生成器。

---

## 一、项目概览

### 1.1 项目是什么

News Agent 是一个自动化工具，它从互联网获取技术新闻（通过 RSS 和 Hacker News API），然后用 AI 大模型整理成一份排版精美的 HTML 日刊。用户可以一键生成包含"网络安全"和"AI"等领域的日刊，也可以定时自动生成（守护模式）。

### 1.2 核心技术栈

| 技术 | 用途 |
|------|------|
| Python 3.14 | 开发语言 |
| AgentScope | Agent 框架，负责调用 AI 大模型生成日刊内容 |
| feedparser | 第三方库，解析 RSS 新闻源 |
| schedule | 第三方库，守护模式的定时调度 |
| asyncio | Python 内置，generator 的 AI 调用是异步的 |
| argparse | Python 内置，CLI 参数解析 |

### 1.3 项目目录结构

```
news-agent/
├── requirements.txt        # 依赖列表（3个核心依赖）
├── README.md               # 使用文档
├── news_agent/             # 主包
│   ├── __init__.py         # 包说明
│   ├── __main__.py         # python -m news_agent 的入口
│   ├── entry/              # 入口模式层：用户如何触发
│   │   ├── __init__.py
│   │   ├── cli.py          # 手动模式 CLI
│   │   └── daemon.py       # 守护模式调度
│   ├── core/               # 核心业务层：获取新闻 + 生成日刊
│   │   ├── __init__.py
│   │   ├── fetcher.py      # 新闻获取 + 分类 + 时间过滤
│   │   └── generator.py    # AI 日刊生成（支持多种模型后端）
│   ├── config/             # 配置与数据层：可定制的部分
│   │   ├── __init__.py
│   │   ├── sources.py      # RSS 源 + 关键词 + 领域定义
│   │   ├── model_factory.py # 模型创建 + 配置加载
│   │   └── config.json     # 默认模型配置文件
│   ├── infra/              # 共享基础设施层
│   │   ├── __init__.py
│   │   └── utils.py        # 日志、输出、包路径常量
│   └── output/             # 日刊输出目录（运行时生成）
│       └── daily_*.html
```

### 1.4 架构设计思想——四层分离

项目采用了**四层分离**的架构：

1. **entry 层**（入口模式）：决定用户如何触发程序——手动 CLI 还是后台守护
2. **core 层**（核心业务）：新闻获取（fetcher）和日刊生成（generator）
3. **config 层**（配置与数据）：RSS源、关键词、模型配置——所有可定制的内容集中在这里
4. **infra 层**（基础设施）：日志、输出目录路径等工具函数，被所有层共享

这种分层的好处：修改 RSS 源只需改 config/sources.py，添加新模型只需改 config/model_factory.py，核心业务逻辑不受影响。

---

## 二、开发步骤详解

下面按照实际开发顺序，从第一步到最后一步，逐一讲解每个文件的编写。

---

### 步骤 1：项目初始化

#### 1.1 创建项目目录和虚拟环境

```bash
mkdir news-agent
cd news-agent
python -m venv .venv

# Windows 激活
.venv\Scripts\activate

# Linux/macOS 激活
source .venv/bin/activate
```

#### 1.2 创建包目录结构

```bash
mkdir news_agent
mkdir news_agent\entry
mkdir news_agent\core
mkdir news_agent\config
mkdir news_agent\infra
mkdir news_agent\output
```

每个子目录都需要 `__init__.py`（空文件即可），Python 才会把它识别为包。

#### 1.3 创建 requirements.txt

```
agentscope>=2.0.1
feedparser>=6.0.11
schedule>=1.2.0
```

只有 3 个核心依赖。`agentscope` 会自动带入 `openai`、`dashscope` 等依赖。

安装：
```bash
pip install -r requirements.txt
```

---

### 步骤 2：infra 层——基础设施

先写基础设施层，因为其他所有层都依赖它。

#### 2.1 `news_agent/__init__.py`

```python
"""News Agent - 技术日刊生成器"""
```

一行文档字符串，说明包用途。

#### 2.2 `news_agent/infra/__init__.py`

空文件。

#### 2.3 `news_agent/infra/utils.py`

这是整个项目的基础工具箱，提供三个东西：

```python
import logging
import os
import sys

PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_DIR = os.path.join(PACKAGE_DIR, "output")

logger = logging.getLogger("news_agent")


def setup_logging(level=logging.INFO):
    root = logging.getLogger("news_agent")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)


def safe_print(text):
    sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
    sys.stdout.buffer.flush()
```

**逐行解析**：

- **`PACKAGE_DIR`**：通过 `__file__` 的绝对路径向上走两层（从 infra/utils.py 到 news_agent/），得到包根目录。这比硬编码路径更健壮，无论项目放在哪里都能正确定位。
- **`DEFAULT_OUTPUT_DIR`**：日刊输出目录，默认在包根目录下的 `output/` 子目录。
- **`setup_logging()`**：配置 news_agent 命名空间的日志。只在首次调用时设置 handler（通过 `if root.handlers` 检查），避免重复添加。输出到 stdout，格式为 `时间 [级别] 消息`。
- **`safe_print()`**：Windows 环境下 stdout 可能遇到编码问题（中文输出乱码），用 `buffer.write` + UTF-8 编码 + `errors="replace"` 确保任何字符都能安全输出。

---

### 步骤 3：config 层——配置与数据

所有可定制的内容集中在这一层，修改配置不需要触碰核心业务代码。

#### 3.1 `news_agent/config/__init__.py`

空文件。

#### 3.2 `news_agent/config/sources.py`

这个文件定义了三件事：RSS 源列表、关键词分类字典、领域标签映射。

```python
RSS_SOURCES = [
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/newest?q=AI+security&count=40",
        "category": "mixed",
    },
    {
        "name": "Hacker News (CVE)",
        "url": "https://hnrss.org/newest?q=CVE+vulnerability+exploit&count=30",
        "category": "security",
    },
    {
        "name": "Hacker News (Cybersec)",
        "url": "https://hnrss.org/newest?q=cybersecurity+hack+ransomware+malware+phishing+breach&count=30",
        "category": "security",
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "ai",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "ai",
    },
    {
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "category": "ai",
    },
]

SEC_KEYWORDS = [
    "security", "cybersecurity", "vulnerability", "CVE", "exploit",
    "malware", "ransomware", "phishing", "zero-day", "breach",
    "hack", "pentest", "OWASP", "DDoS", "APT", "backdoor",
    "trojan", "spyware", "data leak", "encryption", "firewall",
    "incident response", "threat intelligence", "SOC", "CVE-",
    "supply chain attack", "infrastructure attack",
]

AI_KEYWORDS = [
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "GPT", "language model", "neural network", "AGI",
    "ChatGPT", "generative AI", "diffusion", "transformer", "RAG",
    "agent", "fine-tuning", "inference", "benchmark",
    "AI safety", "AI security", "model attack", "prompt injection",
]

BUILTIN_TOPICS = {
    "security": SEC_KEYWORDS,
    "ai": AI_KEYWORDS,
}

TOPIC_LABELS = {
    "security": "网络安全",
    "ai": "AI / 人工智能",
}

HN_API_URL = "https://hacker-news.firebaseio.com/v0"


def build_topics(custom_topics=None):
    if not custom_topics:
        return dict(BUILTIN_TOPICS)
    topics = {}
    for name in custom_topics:
        if name in BUILTIN_TOPICS:
            topics[name] = BUILTIN_TOPICS[name]
        else:
            topics[name] = [name]
    return topics
```

**逐段解析**：

- **`RSS_SOURCES`**：6 个 RSS 源的配置列表。每个源有 `name`（显示名称）、`url`（RSS 地址）、`category`（领域标签）。`category` 为 `"mixed"` 表示该源包含多个领域的新闻（AI+security），其他源明确标记为 `"security"` 或 `"ai"`。
  - Hacker News 的 RSS 通过 hnrss.org 获取，支持关键词查询参数 `q=` 和条数限制 `count=`。
  - TechCrunch、VentureBeat、AI News 是专业的 AI 新闻 RSS 源。

- **`SEC_KEYWORDS`**：26 个网络安全关键词，用于对新闻标题进行分类匹配。
- **`AI_KEYWORDS`**：22 个 AI 关键词，同理。
- **`BUILTIN_TOPICS`**：将关键词分组为领域，`"security"` 和 `"ai"` 是内置的两大领域。
- **`TOPIC_LABELS`**：领域名到中文显示名的映射，用于日刊标题和板块标题的生成。
- **`HN_API_URL`**：Hacker News API 的基础 URL，用于 fetcher 中直接获取热门文章。

- **`build_topics(custom_topics)`**：根据用户传入的领域列表构建 topics 字典。
  - 如果传入 `None` 或空列表，返回所有内置领域。
  - 如果传入 `["ai", "security"]`，返回对应的内置关键词。
  - 如果传入自定义领域如 `"blockchain"`，则用领域名本身作为关键词（`["blockchain"]`），匹配范围较窄但够用。用户如需更精确的关键词，可以自行在 `BUILTIN_TOPICS` 中扩展。

---

#### 3.3 `news_agent/config/model_factory.py`

这是模型配置的核心模块，负责从 JSON 配置文件加载参数、创建 credential、创建 chat model。支持 8 种模型服务商。

```python
import importlib
import json
import logging
import os

logger = logging.getLogger(__name__)

PROVIDER_CREDENTIAL_MAP = {
    "dashscope": ("agentscope.credential", "DashScopeCredential"),
    "openai": ("agentscope.credential", "OpenAICredential"),
    "anthropic": ("agentscope.credential", "AnthropicCredential"),
    "deepseek": ("agentscope.credential", "DeepSeekCredential"),
    "gemini": ("agentscope.credential", "GeminiCredential"),
    "moonshot": ("agentscope.credential", "MoonshotCredential"),
    "ollama": ("agentscope.credential", "OllamaCredential"),
    "xai": ("agentscope.credential", "XAICredential"),
}

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config.json"
)

DEFAULT_CONFIG = {
    "model_provider": "dashscope",
    "model_name": "glm-5.1",
    "api_key_env": "DASHSCOPE_API_KEY",
    "base_url": "",
    "host": "",
    "temperature": 0.5,
    "max_tokens": 8192,
    "context_size": 131072,
}


def load_config(config_path=None):
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    if not os.path.exists(config_path):
        logger.info(f"配置文件不存在，使用默认配置: {config_path}")
        return dict(DEFAULT_CONFIG)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"配置文件读取失败，使用默认配置: {config_path} - {e}")
        return dict(DEFAULT_CONFIG)


def _get_credential_class(provider):
    if provider not in PROVIDER_CREDENTIAL_MAP:
        raise ValueError(
            f"Unsupported model_provider: {provider}. "
            f"Supported: {', '.join(PROVIDER_CREDENTIAL_MAP.keys())}"
        )
    module_name, class_name = PROVIDER_CREDENTIAL_MAP[provider]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def create_credential(provider, api_key_env="", base_url="", host=""):
    cred_class = _get_credential_class(provider)

    if provider == "ollama":
        return cred_class(host=host or None)

    api_key = os.environ.get(api_key_env, "")
    if not api_key and api_key_env:
        raise ValueError(
            f"API key not found in environment variable '{api_key_env}'. "
            f"Please set it before running."
        )

    if provider == "openai":
        return cred_class(api_key=api_key, base_url=base_url or None)
    return cred_class(api_key=api_key)


def create_chat_model(credential, provider, model_name, temperature=0.5,
                      max_tokens=8192, context_size=131072, base_url=""):
    chat_model_class = credential.get_chat_model_class()

    common_kwargs = {
        "credential": credential,
        "model": model_name,
        "stream": False,
        "context_size": context_size,
    }

    if provider == "ollama":
        common_kwargs["parameters"] = chat_model_class.Parameters(
            temperature=temperature,
            num_predict=max_tokens,
        )
    else:
        common_kwargs["parameters"] = chat_model_class.Parameters(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if base_url and provider == "openai":
            common_kwargs["client_kwargs"] = {"base_url": base_url}

    return chat_model_class(**common_kwargs)


def create_model_from_config(config):
    provider = config.get("model_provider", DEFAULT_CONFIG["model_provider"])
    model_name = config.get("model_name", DEFAULT_CONFIG["model_name"])
    api_key_env = config.get("api_key_env", "")
    base_url = config.get("base_url", "")
    host = config.get("host", "")
    temperature = config.get("temperature", DEFAULT_CONFIG["temperature"])
    max_tokens = config.get("max_tokens", DEFAULT_CONFIG["max_tokens"])
    context_size = config.get("context_size", DEFAULT_CONFIG["context_size"])

    credential = create_credential(provider, api_key_env=api_key_env,
                                   base_url=base_url, host=host)
    return create_chat_model(credential, provider, model_name,
                             temperature=temperature, max_tokens=max_tokens,
                             context_size=context_size, base_url=base_url)
```

**逐段解析**：

- **`PROVIDER_CREDENTIAL_MAP`**：一个字典，将 provider 名称映射到 AgentScope 中对应的 Credential 类。使用 `importlib.import_module` 动态导入，避免一次性导入所有 credential 类（有些可能安装时不存在）。支持 8 种 provider：dashscope、openai、anthropic、deepseek、gemini、moonshot、ollama、xai。

- **`DEFAULT_CONFIG_PATH`**：默认配置文件路径，位于 config/ 目录下的 config.json。通过 `os.path.dirname(os.path.abspath(__file__))` 动态计算，确保无论从哪里运行都能找到配置文件。

- **`DEFAULT_CONFIG`**：硬编码的默认配置，使用 DashScope + glm-5.1。当配置文件不存在或读取失败时使用。

- **`load_config(config_path)`**：加载 JSON 配置文件。三层容错：
  1. 文件不存在 → 返回默认配置
  2. JSON 格式错误 → 返回默认配置
  3. 正常 → 返回文件内容

- **`_get_credential_class(provider)`**：动态导入并返回对应的 Credential 类。不支持传入非法 provider 会抛出明确的错误信息。

- **`create_credential(provider, ...)`**：根据 provider 创建 credential 对象。三种特殊情况：
  1. `ollama`：不需要 API Key，只需 host 地址
  2. `openai`：需要 API Key + 可选 base_url（用于 OpenAI 兼容接口）
  3. 其他 provider：只需 API Key
  - API Key 从环境变量读取（通过 `api_key_env` 指定变量名），不直接写在配置文件中，确保安全性。

- **`create_chat_model(credential, ...)`**：根据 credential 和参数创建 chat model 对象。两个特殊情况：
  1. `ollama`：参数名不同（`num_predict` 而非 `max_tokens`）
  2. `openai` + `base_url`：需要通过 `client_kwargs` 传入自定义 API 地址

- **`create_model_from_config(config)`**：一站式函数，从 config 字典 → credential → chat model。generator.py 调用这个函数即可。

**设计要点**：整个 model_factory 采用"配置驱动"的设计理念。添加新的 provider 只需在 `PROVIDER_CREDENTIAL_MAP` 中加一行映射，核心逻辑不需要改动。

---

#### 3.4 `news_agent/config/config.json`

默认的模型配置文件：

```json
{
  "model_provider": "dashscope",
  "model_name": "glm-5.1",
  "api_key_env": "DASHSCOPE_API_KEY",
  "base_url": "",
  "host": "",
  "temperature": 0.5,
  "max_tokens": 8192,
  "context_size": 131072
}
```

字段说明：
- `model_provider`：服务商名，对应 `PROVIDER_CREDENTIAL_MAP` 的 key
- `model_name`：模型名（如 glm-5.1、gpt-4o、claude-sonnet-4-20250514）
- `api_key_env`：存放 API Key 的环境变量名（不是 Key 本身！）
- `base_url`：OpenAI 兼容接口的自定义地址（空字符串表示使用默认地址）
- `host`：Ollama 服务地址（仅 ollama provider 使用）
- `temperature`：生成温度，0.5 适中
- `max_tokens`：最大输出 token 数
- `context_size`：模型上下文窗口大小

---

### 步骤 4：core 层——核心业务逻辑

这是项目的核心，包含两个模块：fetcher（获取新闻）和 generator（生成日刊）。

#### 4.1 `news_agent/core/__init__.py`

空文件。

#### 4.2 `news_agent/core/fetcher.py`

这个模块负责从互联网获取新闻、分类、时间过滤、去重排序。是整个项目的数据入口。

```python
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
```

**逐函数解析**：

- **`_classify(title, topics)`**：新闻分类核心算法。将标题转为小写，遍历所有 topic 的关键词列表，如果标题中包含任一关键词，则标记为该 topic。一条新闻可能同时属于多个 topic（如 AI 安全事件既属于 "ai" 又属于 "security"），用逗号连接返回（如 `"ai,security"`）。如果没有匹配任何关键词，返回 `None`，表示该新闻不在关注范围内。

- **`_parse_date(entry)`**：从 RSS entry 中解析发布时间。feedparser 解析 RSS 后会将时间存为 `published_parsed` 或 `updated_parsed`（9 元元组），取前 6 个元素（年月日时分秒）构造 UTC 时区的 datetime 对象。两层容错：先尝试 published，再尝试 updated；解析失败返回 None。

- **`_extract_image(entry)`**：从 RSS entry 中提取图片 URL。两步策略：
  1. 先检查标准媒体字段 `media_content` 和 `enclosures`，查找含图片扩展名的 URL
  2. 如果没有，从 HTML 内容中用正则 `<img src=...>` 提取第一张图片
  - 返回空字符串表示无图片

- **`_resolve_time_range(days, start_time, end_time)`**：计算时间范围。两种模式：
  1. 精确模式：直接使用传入的 `start_time` 和 `end_time`（晨报模式）
  2. 相对模式：基于当前时间往前推 `days` 天（普通模式）

- **`_fetch_json(url, timeout)`**：通过 urllib 请求 JSON API。设置 User-Agent 头避免被拒，多层异常捕获（URLError、HTTPError、JSONDecodeError、TimeoutError、通用 Exception），所有异常都记录日志并返回 None，不会崩溃。

- **`_make_article(...)`**：构造统一的新闻字典结构，包含 8 个字段：source（来源名）、title、url、date、score（热度）、desc（描述）、image（图片URL）、category（分类）。

- **`fetch_hackernews_top(...)`**：从 HN API 获取热门文章。流程：
  1. 获取 topstories.json（ID 列表）
  2. 遍历前 `limit*3` 个 ID（因为很多文章会被分类/时间过滤掉，所以多取一些）
  3. 对每个 ID 请求详情，分类+时间过滤
  4. 返回符合条件的文章列表
  - 注意：HN API 请求较慢（逐条请求），所以默认不启用，需通过 `--hn-api` 参数开启

- **`fetch_rss(...)`**：从 RSS 源获取新闻。流程：
  1. 遍历 `RSS_SOURCES` 中的每个源
  2. 用 feedparser 解析 RSS feed
  3. 三层容错：请求失败、解析失败（bozo 且无 entries）、无数据
  4. 对每条 entry：解析时间→时间过滤→分类→提取图片→提取描述→构造 article
  - 分类逻辑特殊：如果关键词匹配不到分类，但 RSS 源本身有 category 标记（如 TechCrunch 的 category="ai"），且该 category 在用户关注的 topics 中，则直接用源的 category。这确保了专业 RSS 源的新闻不会因为标题不含关键词而被遗漏。

- **`fetch_all_news(...)`**：汇总入口。先获取 RSS 新闻，如果启用 HN API 再追加。然后去重（按标题小写比较）+ 按热度降序排序。返回最终新闻列表。

**设计要点**：
- 所有内部函数以 `_` 开头，表示模块私有
- 时间过滤支持两种模式（相对天数 vs 精确时间范围），为晨报模式和普通模式共用
- 分类逻辑既有关键词匹配又有源标记 fallback，确保不遗漏
- 网络请求全面容错，不会因为单个源失败而崩溃

---

#### 4.3 `news_agent/core/generator.py`

这是项目的 AI 核心，负责将原始新闻列表交给大模型整理成 HTML 日刊。

```python
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
  /* CSS 内容见下方详解 */
  ...（省略，完整内容见源码）
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
```

**逐段解析**：

- **`HTML_TEMPLATE`**：一个完整的 HTML 页面模板字符串，使用 Python 的 `str.format()` 占位符 `{date}` 和 `{content}`。CSS 部分定义了完整的日刊样式：
  - CSS 变量（`:root`）定义主题色：primary（深蓝）、accent-sec（安全板块红色）、accent-ai（AI板块蓝色）
  - `.header`：渐变背景的头部区域
  - `.card`：新闻卡片样式，hover 时有阴影效果
  - `.card.highlight`：重点关注新闻的左侧橙色边框 + 黄色背景
  - `.badge-focus/watch/general`：三个级别的徽章样式（橙/蓝/灰）
  - `.timeline`：事件时间线的灰色背景区域
  - `.references`：技术引用的绿色背景区域
  - `.summary`：今日总结区域
  - 响应式设计：`max-width: 960px` + `padding: 20px`，手机和 PC 都能良好阅读

- **`SYSTEM_PROMPT`**：给 AI 模型的系统提示词，定义了日刊编辑的完整规范。关键设计：
  1. 要求输出纯 HTML body 内容（不含 html/head/body 标签），因为外层模板已经提供了这些
  2. 新闻三级分级制度：重点关注（badge-focus + 详细解读 + 时间线 + 技术引用）、值得关注（badge-watch + 一句话摘要）、一般动态（badge-general + 仅标题来源）
  3. 重点关注新闻的深度处理要求：事件时间线要追溯根源、技术引用要包含 CVE/论文/教程
  4. 语言要求：中文解读 + 英文标题保留 + 技术术语保留英文
  5. 明确提醒不要把所有新闻都标为重点关注

- **`create_agent(config)`**：创建 AgentScope Agent。使用 `ReActConfig(max_iters=1)` 限制迭代次数为 1（日刊生成是单轮任务，不需要多轮推理）。

- **`_format_raw(n, idx)`**：将新闻字典格式化为文本，传给 AI 模型。包含序号、来源、分类、标题、链接、日期、描述、热度、图片 URL。

- **`_build_fallback_html(news_list, date_str, topics)`**：AI 调用失败时的回退方案。生成一个简单的 HTML，只有标题+来源+日期，没有 AI 解读。标题动态生成：将多个领域标签用"与"连接（如"网络安全与AI技术日刊"）。

- **`_extract_body_from_full_html(html_body)`**：有些 AI 模型会输出完整的 HTML 页面（包含 `<html><body>` 标签），需要提取 body 内的内容。通过正则匹配 `<body>...</body>` 提取。如果输入本身就是 body 内容，则直接返回。

- **`generate_bulletin(...)`**：核心生成函数（异步）。流程：
  1. 处理空新闻情况（返回"今日未获取到相关新闻"的页面）
  2. 按领域分组新闻，格式化为文本
  3. 动态构建 prompt（根据 topics 参数生成板块描述）
  4. 创建 Agent，发送 UserMsg
  5. 等待 AI 返回 HTML body 内容
  6. 如果 AI 调用失败，使用 `_build_fallback_html` 回退
  7. 将 HTML body 嵌入 `HTML_TEMPLATE`

- **`generate_bulletin_to_file(...)`**：将日刊写入文件。流程：
  1. 确保输出目录存在（`os.makedirs(exist_ok=True)`）
  2. 调用 `generate_bulletin` 生成 HTML
  3. 文件名精确到秒：`daily_YYYYMMDD_HHMMSS.html`，避免同一时间段多次生成覆盖
  4. UTF-8 编码写入
  5. 用 `safe_print` 输出文件路径

**设计要点**：
- 异步设计：`generate_bulletin` 和 `generate_bulletin_to_file` 都是 async 函数，因为 AgentScope 的 `agent.reply` 是异步的
- 双重容错：AI 调用失败时有 fallback HTML，空新闻时有友好提示页面
- 动态 prompt：根据 topics 参数动态构建板块描述，支持任意领域组合
- 模板与内容分离：HTML_TEMPLATE 提供框架，AI 只生成 body 内容

---

### 步骤 5：entry 层——入口模式

#### 5.1 `news_agent/entry/__init__.py`

空文件。

#### 5.2 `news_agent/entry/cli.py`

手动模式的 CLI 入口，用户通过命令行参数触发一次日刊生成。

```python
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
```

**逐段解析**：

- **`run_once(...)`**：执行一次完整的日刊生成流程（异步函数）。
  1. 用 `build_topics` 将用户传入的领域列表转为 topics 字典
  2. 输出进度信息（正在获取...获取到 N 条...调用模型...）
  3. 调用 `fetch_all_news` 获取新闻
  4. 显示前 5 条新闻的标题
  5. 显示正在使用的模型信息
  6. 调用 `generate_bulletin_to_file` 生成日刊

- **`parse_date(date_input)`**：验证日期格式，必须是 YYYY-MM-DD。

- **`parse_time_str(time_str)`**：验证时间格式 HH:MM，并检查范围（0-23 小时，0-59 分钟）。返回 (hour, minute) 元组。

- **`main()`**：CLI 主函数。流程：
  1. 初始化日志
  2. 定义 argparse 参数（9 个参数）
  3. 解析参数，验证格式
  4. 如果 `--morning` 模式：计算 start_time（昨天 0:00 UTC）和 end_time（今天指定时间 UTC）
  5. 如果 `--daemon`：转入守护模式
  6. 否则：用 `asyncio.run` 执行一次 `run_once`

**参数说明**：
- `--days N`：获取最近 N 天的新闻
- `--date YYYY-MM-DD`：指定日刊日期
- `--output DIR`：输出目录
- `--hn-api`：启用 HN API（较慢但数据多）
- `--topics ai,security,...`：指定领域，逗号分隔
- `--config PATH`：自定义模型配置文件
- `--daemon`：守护模式
- `--morning`：晨报模式
- `--time HH:MM`：守护模式的每日执行时间 / 晨报截止时间

**晨报模式的时间计算**：
```python
now = datetime.now(timezone.utc)
start_time = datetime(now.year, now.month, now.day - 1, 0, 0, 0, tzinfo=timezone.utc)
end_time = datetime(now.year, now.month, now.day, hour, minute, 0, tzinfo=timezone.utc)
```
- start_time：昨天 0:00 UTC（`now.day - 1`）
- end_time：今天指定时间 UTC
- 这确保晨报只包含"昨天全天到今天早上"的新闻

---

#### 5.3 `news_agent/entry/daemon.py`

守护模式，每天定时自动生成日刊。

```python
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
```

**逐段解析**：

- **`_running`**：全局标志，控制守护循环是否继续运行。

- **`_signal_handler(sig, frame)`**：信号处理函数。收到 SIGINT（Ctrl+C）或 SIGTERM 时，将 `_running` 设为 False，守护循环会在下一次检查时退出。

- **`_generate_job(...)`**：异步的日刊生成任务。和 cli.py 的 `run_once` 类似，但不输出到 stdout（只用 logger），因为守护模式是后台运行。

- **`_scheduled_job(...)`**：schedule 库的回调函数（必须是同步函数）。内部用 `asyncio.run` 调用异步的 `_generate_job`。如果启用了晨报模式，计算 start_time 和 end_time。

- **`run_daemon(...)`**：守护模式主函数。流程：
  1. 初始化日志
  2. 设置信号处理
  3. 如果晨报模式：解析时间，计算 morning_hour
  4. 用 `schedule.every().day.at(time_str).do(...)` 注册定时任务
  5. 进入守护循环：每 60 秒检查一次是否有待执行的定时任务
  6. 收到停止信号后退出循环

**设计要点**：
- 守护循环用 `time.sleep(60)` 而非更短间隔，因为日刊生成是每天一次的任务，60 秒的检查频率足够
- `_scheduled_job` 是同步函数包裹异步函数，因为 schedule 库不支持异步回调
- 守护期间不消耗 AI token（只在定时任务触发时才调用模型）

---

### 步骤 6：`__main__.py`——python -m 入口

```python
from news_agent.entry.cli import main

main()
```

这 3 行代码使得用户可以通过 `python -m news_agent` 运行程序。Python 的 `-m` 参数会在目标包中查找 `__main__.py` 并执行它。

---

## 三、数据流全景

一次完整的日刊生成流程：

```
用户命令 python -m news_agent --days 1 --topics ai,security
    │
    ▼
__main__.py → cli.main()
    │
    ▼
argparse 解析参数 → load_config() 加载模型配置
    │
    ▼
cli.run_once()
    │
    ├──► fetcher.fetch_all_news()
    │       ├──► fetch_rss() → feedparser 解析 6 个 RSS 源
    │       │     每条新闻：_parse_date → 时间过滤 → _classify → 分类
    │       │     → _extract_image → _make_article
    │       ├──► fetch_hackernews_top()（可选）
    │       └──► 去重 + 按热度排序 → 返回新闻列表
    │
    ├──► generator.generate_bulletin_to_file()
    │       ├──► generate_bulletin()
    │       │     ├──► 构建动态 prompt（按领域分组新闻文本）
    │       │     ├──► create_agent() → Agent(news_editor, system_prompt, model)
    │       │     ├──► agent.reply(UserMsg) → AI 返回 HTML body 内容
    │       │     ├──► _extract_body_from_full_html() → 提取 body
    │       │     ├──► HTML_TEMPLATE.format() → 完整 HTML 页面
    │       │     └──► fallback: _build_fallback_html()（AI 失败时）
    │       ├──► 写入文件 daily_YYYYMMDD_HHMMSS.html
    │       └──► safe_print 输出文件路径
    │
    ▼
用户收到: "日刊已生成: news_agent/output/daily_20260615_011418.html"
```

---

## 四、关键设计决策详解

### 4.1 为什么用 AgentScope 而不是直接调 OpenAI SDK？

AgentScope 提供了统一的 Agent 抽象层：
- `Agent` 类封装了 system_prompt + model + reply 方法，一行代码创建
- `ReActConfig` 支持推理+行动模式，虽然日刊生成只需单轮，但框架为后续扩展留了空间
- 内置 8 种 Credential 类，统一了不同服务商的认证方式
- `UserMsg` 标准化了消息格式

如果直接用 OpenAI SDK，需要自己处理不同服务商的 API 格式差异、认证方式、错误处理等。AgentScope 把这些都封装好了。

### 4.2 为什么 generator 是异步的？

AgentScope 的 `agent.reply()` 方法是异步的（返回 coroutine）。因此 `generate_bulletin` 和 `generate_bulletin_to_file` 必须是 `async def`，在 cli.py 中通过 `asyncio.run()` 调用。

守护模式的 `_scheduled_job` 是同步函数（schedule 库要求），内部用 `asyncio.run()` 调用异步函数。

### 4.3 为什么 API Key 用环境变量而非配置文件？

安全性。如果 API Key 写在 config.json 中，容易被误提交到 Git 仓库。用 `api_key_env` 指定环境变量名，Key 本体只存在于运行环境中，不会泄露到文件。

### 4.4 为什么文件名精确到秒？

不同时间、不同领域的日刊不应互相覆盖。`daily_YYYYMMDD_HHMMSS.html` 确保每次生成都是独立文件。

### 4.5 为什么分类有双重逻辑？

RSS 源的新闻标题不一定包含关键词（如 TechCrunch 的 AI 文章标题可能只写产品名），但 RSS 源本身标记了 category。双重逻辑确保：
1. 关键词匹配：捕获标题中明确包含领域关键词的新闻
2. 源标记 fallback：捕获专业源中标题不含关键词但确实属于该领域的新闻

---

## 五、常见问题与开发提示

### 5.1 运行时报 `ModuleNotFoundError`

确保在项目根目录（`news-agent/`）下执行 `python -m news_agent`，不要在子目录内执行。

### 5.2 Windows 下中文输出乱码

`safe_print` 函数专门解决了这个问题，用 `sys.stdout.buffer.write` + UTF-8 编码。所有面向用户的输出都应使用 `safe_print` 而非 `print`。

### 5.3 AI 模型返回了完整的 HTML 页面

有些模型会忽略"只输出 body 内容"的要求，返回 `<html><body>...</body></html>`。`_extract_body_from_full_html` 函数处理了这种情况，通过正则提取 body 内容。

### 5.4 如何添加新的 RSS 源？

编辑 `config/sources.py` 的 `RSS_SOURCES` 列表，添加新条目：
```python
{
    "name": "新源名称",
    "url": "https://example.com/feed/",
    "category": "ai",  # 或 "security" 或 "mixed"
}
```

### 5.5 如何添加新的模型服务商？

在 `config/model_factory.py` 的 `PROVIDER_CREDENTIAL_MAP` 中添加映射：
```python
"new_provider": ("agentscope.credential", "NewProviderCredential"),
```
前提是 AgentScope 已支持该 Credential 类。

### 5.6 如何扩展领域关键词？

编辑 `config/sources.py`：
```python
BUILTIN_TOPICS = {
    "security": SEC_KEYWORDS,
    "ai": AI_KEYWORDS,
    "blockchain": ["blockchain", "crypto", "NFT", "Web3", "DeFi"],
}
TOPIC_LABELS = {
    "security": "网络安全",
    "ai": "AI / 人工智能",
    "blockchain": "区块链",
}
```

---

## 六、从 0 到 1 的开发顺序建议

1. **infra/utils.py** → 先写基础设施，所有模块依赖它
2. **config/sources.py** → 定义数据源和关键词，fetcher 依赖它
3. **config/config.json + model_factory.py** → 定义模型配置，generator 依赖它
4. **core/fetcher.py** → 新闻获取，这是数据入口
5. **core/generator.py** → 日刊生成，这是 AI 核心
6. **entry/cli.py** → CLI 入口，串联所有模块
7. **entry/daemon.py** → 守护模式，基于 cli 的逻辑扩展
8. **__main__.py + __init__.py** → 包入口，3 行代码
9. **requirements.txt** → 依赖声明
10. **测试运行** → `python -m news_agent` 验证

每个模块完成后都可以单独测试（如 fetcher 可以直接调用 `fetch_all_news()` 看返回结果），不需要等到全部写完。

---

## 七、完整源码速查

所有源码已在上方逐文件讲解。如需快速查阅，文件对应关系：

| 文件 | 行数 | 核心职责 |
|------|------|---------|
| infra/utils.py | 25 | 日志初始化、安全输出、包路径常量 |
| config/sources.py | 73 | RSS源、关键词、领域定义、build_topics |
| config/model_factory.py | 119 | 模型配置加载、credential创建、chat model创建 |
| config/config.json | 10 | 默认模型配置（DashScope + glm-5.1） |
| core/fetcher.py | 211 | RSS获取、HN API获取、分类、时间过滤、去重 |
| core/generator.py | 380 | HTML模板、system prompt、Agent创建、日刊生成、回退 |
| entry/cli.py | 144 | CLI参数解析、一次生成流程、晨报时间计算 |
| entry/daemon.py | 106 | 定时调度、信号处理、守护循环 |

总计约 **1128 行** Python 代码 + 10 行 JSON，3 个外部依赖。
