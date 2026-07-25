from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
import streamlit as st

from ui.auth import auth_headers


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@st.cache_resource
def _session_factory():
    from app.db.database import SessionLocal, init_db

    init_db()
    return SessionLocal


def _direct_request(method: str, path: str, payload: dict[str, Any] | None, params: dict[str, Any] | None) -> dict:
    from app.services.news_service import (
        analyze_article,
        fetch_and_store,
        list_articles_translated,
        top_topic_pool_translated,
    )
    from app.services.script_service import generate_from_article, generate_from_topic
    from app.services.web3_hot_service import fetch_and_store_hot_items, list_hot_items
    from app.trading_cognition.service import generate_trading_cognition

    db = _session_factory()()
    try:
        payload = payload or {}
        params = params or {}
        if method == "POST" and path == "/api/news/fetch":
            return _run_async(fetch_and_store(db))
        if method == "GET" and path == "/api/news/list":
            return {
                "items": _run_async(
                    list_articles_translated(
                        db,
                        params.get("category"),
                        params.get("keyword"),
                        params.get("time_range"),
                        int(params.get("limit") or 50),
                    )
                )
            }
        if method == "GET" and path == "/api/news/topics":
            return {
                "items": _run_async(
                    top_topic_pool_translated(
                        db,
                        params.get("category"),
                        params.get("keyword"),
                        params.get("time_range"),
                        int(params.get("limit") or 10),
                    )
                )
            }
        if method == "POST" and path == "/api/news/analyze":
            return _run_async(
                analyze_article(
                    db,
                    int(payload["article_id"]),
                    bool(payload.get("use_llm", True)),
                )
            )
        if method == "POST" and path == "/api/script/from_article":
            return _run_async(
                generate_from_article(
                    db,
                    int(payload["article_id"]),
                    payload.get("duration", "3分钟"),
                    payload.get("platform", "抖音"),
                    bool(payload.get("use_llm", True)),
                    payload.get("custom_prompt", ""),
                )
            )
        if method == "POST" and path == "/api/script/from_topic":
            return _run_async(
                generate_from_topic(
                    db,
                    payload.get("topic", ""),
                    payload.get("duration", "3分钟"),
                    payload.get("platform", "抖音"),
                    bool(payload.get("use_llm", True)),
                    payload.get("custom_prompt", ""),
                )
            )
        if method == "POST" and path == "/api/trading-cognition/generate":
            return _run_async(
                generate_trading_cognition(
                    db,
                    payload.get("question", ""),
                    payload.get("duration", "3分钟"),
                    payload.get("platform", "抖音"),
                    bool(payload.get("use_llm", True)),
                    int(payload.get("knowledge_limit") or 4),
                )
            )
        if method == "POST" and path == "/api/web3-hot/fetch-now":
            return _run_async(
                fetch_and_store_hot_items(
                    db,
                    source_type=payload.get("source_type"),
                    keyword=payload.get("keyword"),
                )
            )
        if method == "GET" and path == "/api/web3-hot/list":
            return {
                "items": list_hot_items(
                    db,
                    limit=int(params.get("limit") or 30),
                    heat_level=params.get("heat_level"),
                    trend_status=params.get("trend_status"),
                    keyword=params.get("keyword"),
                    source_type=params.get("source_type"),
                    hours=int(params.get("hours") or 24),
                )
            }
        raise ValueError(f"Unsupported direct request: {method} {path}")
    finally:
        db.close()


def api_request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 180,
) -> dict:
    api_base = os.getenv("API_BASE_URL", "").rstrip("/")
    if not api_base:
        return _direct_request(method.upper(), path, payload, params)

    with httpx.Client(timeout=timeout) as client:
        response = client.request(
            method.upper(),
            f"{api_base}{path}",
            json=payload,
            params=params,
            headers=auth_headers(),
        )
    if response.is_error:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ValueError(str(detail or f"HTTP {response.status_code}"))
    return response.json()
