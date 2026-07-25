from __future__ import annotations

import os
from typing import Any

import streamlit as st


SECRET_ALIASES = {
    "OPENAI_API_KEY": ("OPENAI_API_KEY", "openai_api_key", "api_key"),
    "OPENAI_BASE_URL": ("OPENAI_BASE_URL", "openai_base_url", "base_url"),
    "OPENAI_MODEL": ("OPENAI_MODEL", "openai_model", "model"),
    "DATABASE_URL": ("DATABASE_URL", "database_url"),
    "API_BASE_URL": ("API_BASE_URL", "api_base_url"),
    "RSS_MAX_ARTICLES_PER_SOURCE": ("RSS_MAX_ARTICLES_PER_SOURCE", "rss_max_articles_per_source"),
    "RSS_TIMEOUT_SECONDS": ("RSS_TIMEOUT_SECONDS", "rss_timeout_seconds"),
    "X_BEARER_TOKEN": ("X_BEARER_TOKEN", "x_bearer_token"),
    "LUNARCRUSH_API_KEY": ("LUNARCRUSH_API_KEY", "lunarcrush_api_key"),
}


def _secret_value(secrets: dict[str, Any], env_key: str) -> str | None:
    aliases = SECRET_ALIASES.get(env_key, (env_key,))
    for alias in aliases:
        if alias in secrets:
            return str(secrets[alias])
    for section_name in ("openai", "llm", "general", "app"):
        section = secrets.get(section_name)
        if hasattr(section, "items"):
            section = dict(section)
            for alias in aliases:
                if alias in section:
                    return str(section[alias])
    return None


def configure_environment() -> None:
    """Load Streamlit secrets before application services cache settings."""
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}

    for env_key in SECRET_ALIASES:
        value = _secret_value(secrets, env_key)
        if value and env_key not in os.environ:
            os.environ[env_key] = value
