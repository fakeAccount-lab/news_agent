# News Agent - 技术日刊生成器

基于 AgentScope 的自动化技术新闻日刊生成工具。从 RSS 和 Hacker News 获取新闻，经 AI 智能整理，生成排版精美的 HTML 日刊。支持多种 AI 模型后端。

## 功能特性

- 自动从多个 RSS 源和 Hacker News API 获取技术新闻
- AI 驱动的新闻整理：分级标注、深度解读、事件时间线、技术引用
- 输出精美的 HTML 日刊，支持手机/PC 阅读
- 支持多种 AI 模型后端：DashScope、OpenAI、Anthropic、DeepSeek、Gemini、Moonshot、Ollama、XAI，以及任何 OpenAI 兼容接口
- 灵活的领域配置：内置 AI 和网络安全领域，支持自定义任意领域
- 晨报模式：精确获取昨天全天到指定时间之前的新闻
- 守护模式：每天定时自动生成日刊
- 文件命名精确到秒，同一时间多次生成不会覆盖

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd news-agent
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

核心依赖（3 个，其余由 agentscope 自动带入）：

| 包 | 用途 |
|---|------|
| `agentscope` | Agent 框架，调用各种 AI 模型生成日刊 |
| `feedparser` | RSS 新闻源解析 |
| `schedule` | 守护模式定时调度 |

### 3. 配置模型

模型配置通过 `news_agent/config/config.json` 文件管理。默认配置使用 DashScope（glm-5.1）：

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

根据你使用的模型服务商，修改 `config.json` 并设置对应的环境变量。

#### 配置字段说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `model_provider` | 模型服务商，见下方支持列表 | `"dashscope"` |
| `model_name` | 模型名称 | `"glm-5.1"` |
| `api_key_env` | 存放 API Key 的环境变量名 | `"DASHSCOPE_API_KEY"` |
| `base_url` | 自定义 API 地址（用于 OpenAI 兼容接口） | `""` |
| `host` | Ollama 服务地址（仅 ollama provider） | `""` |
| `temperature` | 生成温度 | `0.5` |
| `max_tokens` | 最大输出 token 数 | `8192` |
| `context_size` | 模型上下文窗口大小 | `131072` |

**关于 API Key 安全性**：`api_key_env` 指定环境变量名而非直接填写 API Key 值，避免密钥泄露到配置文件中。

#### 支持的模型服务商

| Provider | `model_provider` 值 | 环境变量 | 说明 |
|----------|---------------------|----------|------|
| 阿里云 DashScope | `dashscope` | `DASHSCOPE_API_KEY` | 默认，glm 系列模型 |
| OpenAI | `openai` | `OPENAI_API_KEY` | GPT-4o、GPT-4 等 |
| OpenAI 兼容接口 | `openai` | 自定义 | 通过 `base_url` 接入任何兼容接口 |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | Claude 系列 |
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` | DeepSeek 系列 |
| Google Gemini | `gemini` | `GEMINI_API_KEY` | Gemini 系列 |
| Moonshot | `moonshot` | `MOONSHOT_API_KEY` | Kimi 系列 |
| Ollama（本地） | `ollama` | 无需 | 本地部署模型 |
| xAI | `xai` | `XAI_API_KEY` | Grok 系列 |

#### 各服务商配置示例

**DashScope（默认，无需修改）**：
```json
{
  "model_provider": "dashscope",
  "model_name": "glm-5.1",
  "api_key_env": "DASHSCOPE_API_KEY"
}
```
```bash
# 设置环境变量
export DASHSCOPE_API_KEY="sk-xxx"       # Linux/macOS
$env:DASHSCOPE_API_KEY = "sk-xxx"       # Windows PowerShell
```

**OpenAI**：
```json
{
  "model_provider": "openai",
  "model_name": "gpt-4o",
  "api_key_env": "OPENAI_API_KEY"
}
```
```bash
export OPENAI_API_KEY="sk-xxx"
```

**OpenAI 兼容接口（如 DashScope 兼容模式、vLLM、LocalAI 等）**：
```json
{
  "model_provider": "openai",
  "model_name": "glm-5.1",
  "api_key_env": "DASHSCOPE_API_KEY",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
}
```
任何提供 OpenAI 格式 API 的服务都可以通过 `base_url` 接入，包括：
- 阿里云 DashScope 兼容模式
- 本地 vLLM 服务（如 `http://localhost:8000/v1`）
- LocalAI
- LiteLLM 代理
- 其他兼容接口

**Anthropic Claude**：
```json
{
  "model_provider": "anthropic",
  "model_name": "claude-sonnet-4-20250514",
  "api_key_env": "ANTHROPIC_API_KEY"
}
```
```bash
export ANTHROPIC_API_KEY="sk-ant-xxx"
```

**DeepSeek**：
```json
{
  "model_provider": "deepseek",
  "model_name": "deepseek-chat",
  "api_key_env": "DEEPSEEK_API_KEY"
}
```
```bash
export DEEPSEEK_API_KEY="sk-xxx"
```

**Google Gemini**：
```json
{
  "model_provider": "gemini",
  "model_name": "gemini-2.5-pro",
  "api_key_env": "GEMINI_API_KEY"
}
```
```bash
export GEMINI_API_KEY="xxx"
```

**Moonshot（Kimi）**：
```json
{
  "model_provider": "moonshot",
  "model_name": "moonshot-v1-128k",
  "api_key_env": "MOONSHOT_API_KEY"
}
```
```bash
export MOONSHOT_API_KEY="sk-xxx"
```

**Ollama（本地模型，无需 API Key）**：
```json
{
  "model_provider": "ollama",
  "model_name": "qwen2.5:7b",
  "host": "http://localhost:11434",
  "context_size": 32768,
  "max_tokens": 4096
}
```
确保已安装并运行 [Ollama](https://ollama.ai)，且指定模型已拉取（如 `ollama pull qwen2.5:7b`）。

**xAI（Grok）**：
```json
{
  "model_provider": "xai",
  "model_name": "grok-3",
  "api_key_env": "XAI_API_KEY"
}
```
```bash
export XAI_API_KEY="xai-xxx"
```

#### 使用自定义配置文件

可以用 `--config` 指定不同的配置文件，方便在不同模型间切换：

```bash
# 使用默认配置
python -m news_agent

# 使用自定义配置文件
python -m news_agent --config ./my_openai_config.json

# 晨报模式 + 自定义配置
python -m news_agent --morning --config ./my_claude_config.json
```

### 4. 生成日刊

配置完成后，在项目根目录下执行：

```bash
python -m news_agent
```

生成的 HTML 文件位于 `news_agent/output/` 目录。

---

## 使用方法

所有命令均在项目根目录下执行（需先激活虚拟环境）。

### 基础模式

| 命令 | 说明 |
|------|------|
| `python -m news_agent` | 获取最近 1 天的 AI 与网络安全新闻（默认） |
| `python -m news_agent --days 7` | 获取最近 7 天的新闻 |
| `python -m news_agent --days 30` | 获取最近 30 天的新闻 |

### 自定义领域（--topics）

| 命令 | 说明 |
|------|------|
| `python -m news_agent --topics ai,security` | 默认：AI + 网络安全（与不加参数相同） |
| `python -m news_agent --topics ai` | 仅 AI 领域 |
| `python -m news_agent --topics security` | 仅网络安全领域 |
| `python -m news_agent --topics ai,security,blockchain` | AI + 安全 + 区块链 |
| `python -m news_agent --topics quantum` | 量子计算领域 |

**内置领域**有丰富的关键词列表（`ai` 含 22 个关键词，`security` 含 26 个关键词），匹配精度高。

**自定义领域**使用领域名本身作为关键词。例如 `--topics blockchain` 会匹配标题中包含 "blockchain" 的新闻。如需更精确的关键词，可在 `news_agent/fetcher.py` 的 `BUILTIN_TOPICS` 中扩展。

### 晨报模式（--morning）

精确获取「昨天 00:00 到今天指定时间」的新闻，适合每天早上阅读：

| 命令 | 说明 |
|------|------|
| `python -m news_agent --morning` | 昨天 0:00 ~ 今天 06:00 的新闻 |
| `python -m news_agent --morning --time 07:00` | 昨天 0:00 ~ 今天 07:00 的新闻 |
| `python -m news_agent --morning --topics ai,security,quantum` | 晨报 + 自定义领域 |

### 守护模式（--daemon）

后台持续运行，每天定时自动生成日刊：

| 命令 | 说明 |
|------|------|
| `python -m news_agent --daemon --time 08:00` | 每天 08:00 自动生成（最近 1 天新闻） |
| `python -m news_agent --daemon --morning --time 06:00` | 每天 06:00 生成昨天 0:00~06:00 的晨报 |
| `python -m news_agent --daemon --days 3 --time 08:00` | 每天 08:00 生成最近 3 天的新闻 |

守护模式运行期间静默等待，不消耗 AI token。按 `Ctrl+C` 停止。

### 参数组合示例

```bash
# 最近一周 AI + 区块链新闻，使用 Claude 模型
python -m news_agent --days 7 --topics ai,blockchain --config ./claude_config.json

# 晨报模式 + Ollama 本地模型
python -m news_agent --morning --config ./ollama_config.json

# 守护模式：每天 6 点晨报 + DashScope 兼容接口
python -m news_agent --daemon --morning --time 06:00 --config ./dashscope_compat_config.json
```

---

## 输出说明

### 文件命名

格式：`daily_YYYYMMDD_HHMMSS.html`

示例：`daily_20260615_011418.html`

命名精确到秒，同一时间段多次生成不同领域的日刊不会互相覆盖。

### 日刊内容结构

每份日刊包含以下部分（按实际配置的领域动态生成）：

- **页面头部**：日刊标题 + 日期徽章
- **各领域板块**：每个 `--topics` 指定的领域一个独立板块
- **今日总结**：概括各领域主要趋势
- **页脚**

每条新闻分为三个级别：

| 级别 | 标注 | 内容 |
|------|------|------|
| 重点关注 | `badge-focus` | 详细解读 + 事件时间线 + 技术/信息引用 |
| 值得关注 | `badge-watch` | 一句话摘要 |
| 一般动态 | `badge-general` | 仅标题 + 来源 |

---

## 新闻源

当前内置的 RSS 源：

| 源 | 领域 |
|----|------|
| Hacker News (AI + Security) | 综合 |
| Hacker News (CVE) | 网络安全 |
| Hacker News (Cybersec) | 网络安全 |
| TechCrunch AI | AI |
| VentureBeat AI | AI |
| AI News | AI |

启用 `--hn-api` 后还会从 Hacker News API 获取热门文章（数据更多但速度较慢）。

---

## 常见问题

### Q: 执行命令报 `ModuleNotFoundError: No module named 'news_agent'`

确保在**项目根目录**（`news-agent/`）下执行命令，不要在 `news_agent/` 子目录内执行。正确命令为 `python -m news_agent`。

### Q: 报错 `API key not found in environment variable 'XXX'`

未设置对应的 API Key 环境变量。根据 `config/config.json` 中 `api_key_env` 字段指定的名称，设置环境变量：

```bash
# 例如 config.json 中 api_key_env 为 "OPENAI_API_KEY"
export OPENAI_API_KEY="sk-xxx"          # Linux/macOS
$env:OPENAI_API_KEY = "sk-xxx"          # Windows PowerShell
```

### Q: 如何切换到不同的模型？

编辑 `news_agent/config/config.json`，修改 `model_provider` 和 `model_name` 字段。或创建多个配置文件，用 `--config` 参数切换：

```bash
# 准备多个配置文件
cp news_agent/config/config.json openai_config.json
# 编辑 openai_config.json，改为 openai provider

# 使用时指定
python -m news_agent --config openai_config.json
```

### Q: 我的模型 API 不是 OpenAI 格式，怎么接入？

AgentScope 内置了多种服务商的专用接口（DashScope、Anthropic、DeepSeek、Gemini、Moonshot、Ollama、xAI），在 `model_provider` 中指定对应服务商即可。

如果你的服务商不在列表中，但提供了 **OpenAI 兼容接口**（很多服务商都支持），可以通过 `model_provider: "openai"` + `base_url` 接入：

```json
{
  "model_provider": "openai",
  "model_name": "your-model-name",
  "api_key_env": "YOUR_API_KEY_ENV_VAR",
  "base_url": "https://your-service.com/v1"
}
```

如果你的服务商既不在内置列表中、也不提供 OpenAI 兼容接口，则当前不支持。你可以在 `news_agent/config/model_factory.py` 的 `PROVIDER_CREDENTIAL_MAP` 中扩展新的 provider。

### Q: 获取到的新闻数量很少

1. 尝试增大时间范围：`--days 3` 或更多
2. 启用 Hacker News API：`--hn-api`
3. 新闻源内容受 RSS 源更新频率影响，实时新闻量波动正常

### Q: 自定义领域匹配不到新闻

自定义领域使用领域名本身作为关键词，匹配范围较窄。如需扩展关键词，编辑 `news_agent/config/sources.py` 中的 `BUILTIN_TOPICS` 字典：

```python
BUILTIN_TOPICS = {
    "security": SEC_KEYWORDS,
    "ai": AI_KEYWORDS,
    "blockchain": ["blockchain", "crypto", "NFT", "Web3", "DeFi", "smart contract"],
    "quantum": ["quantum", "quantum computing", "qubit", "quantum cryptography"],
}
```

---

## 项目结构

```
news-agent/
├── requirements.txt        # 依赖列表
├── README.md               # 使用文档
├── news_agent/
│   ├── __init__.py         # 包说明
│   ├── __main__.py         # 入口（python -m news_agent）
│   ├── entry/              # 入口模式（用户如何触发）
│   │   ├── cli.py          # 手动模式 CLI
│   │   └── daemon.py       # 守护模式调度
│   ├── core/               # 核心业务逻辑
│   │   ├── fetcher.py      # 新闻获取 + 分类 + 时间过滤
│   │   └── generator.py    # AI 日刊生成（支持多种模型后端）
│   ├── config/             # 配置与数据（可定制）
│   │   ├── sources.py      # RSS 源 + 关键词 + 领域定义
│   │   ├── model_factory.py # 模型创建 + 配置加载
│   │   └── config.json     # 默认模型配置
│   ├── infra/              # 共享基础设施
│   │   └── utils.py        # 日志、输出、包路径常量
│   └── output/             # 日刊输出目录（运行时生成）
│       └── daily_*.html
```