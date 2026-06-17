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