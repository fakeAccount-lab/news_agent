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