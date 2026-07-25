from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import BASE_DIR, settings
from app.services.web3_hot_collectors.base import BaseHotFeedCollector, HotCollectorResult, HotFeedItem


X_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,15}$")
X_QUERY_SUFFIX = " -is:retweet"


def load_x_key_accounts(path: Path | None = None) -> list[dict[str, Any]]:
    config_path = path or BASE_DIR / "config" / "x_key_accounts.json"
    with config_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    accounts = data.get("accounts", [])
    if not isinstance(accounts, list):
        raise ValueError("X 重点账号配置中的 accounts 必须是数组")
    return [dict(item) for item in accounts if isinstance(item, dict)]


def build_account_queries(
    accounts: list[dict[str, Any]],
    max_length: int = 512,
) -> list[str]:
    queries: list[str] = []
    batch: list[str] = []

    for account in accounts:
        username = str(account.get("username", "")).strip().lstrip("@")
        if not account.get("enabled", True) or not X_USERNAME_PATTERN.fullmatch(username):
            continue
        term = f"from:{username}"
        candidate_terms = [*batch, term]
        candidate = f"({' OR '.join(candidate_terms)}){X_QUERY_SUFFIX}"
        if batch and len(candidate) > max_length:
            queries.append(f"({' OR '.join(batch)}){X_QUERY_SUFFIX}")
            batch = [term]
        else:
            batch = candidate_terms

    if batch:
        queries.append(f"({' OR '.join(batch)}){X_QUERY_SUFFIX}")
    return queries


class XRecentSearchCollector(BaseHotFeedCollector):
    QUERY = '(BTC OR Bitcoin OR ETH OR Ethereum OR ETF OR MicroStrategy OR Strategy OR hack OR depeg OR Binance OR Coinbase) lang:en -is:retweet'

    async def fetch(self, source_type: str | None = None, keyword: str | None = None) -> HotCollectorResult:
        result = HotCollectorResult()
        if source_type and source_type != "x_recent_search":
            return result
        source = next((item for item in self.sources if item.get("type") == "x_recent_search"), None)
        if not source or not source.get("enabled", False):
            return result
        if not settings.x_bearer_token:
            result.errors.append("X API 未配置，已跳过 X Recent Search")
            return result

        query = keyword or self.QUERY
        headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
        params = {
            "query": query,
            "max_results": min(self.max_items_per_source, 100),
            "tweet.fields": "created_at,public_metrics,author_id,lang",
        }
        try:
            async with httpx.AsyncClient(timeout=20, headers=headers) as client:
                response = await client.get("https://api.x.com/2/tweets/search/recent", params=params)
                response.raise_for_status()
            data = response.json()
            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                created_at = None
                if tweet.get("created_at"):
                    created_at = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                result.items.append(
                    HotFeedItem(
                        source_name=source.get("name", "X Crypto Search"),
                        source_type="x_recent_search",
                        source_priority=source.get("priority", "P1"),
                        title=tweet.get("text", "")[:240],
                        content=tweet.get("text", ""),
                        summary=tweet.get("text", "")[:280],
                        link=f"https://x.com/i/web/status/{tweet.get('id')}",
                        author=tweet.get("author_id"),
                        published_at=created_at,
                        language=tweet.get("lang"),
                        raw_metrics={
                            "likes": metrics.get("like_count", 0),
                            "reposts": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                            "quotes": metrics.get("quote_count", 0),
                        },
                        raw_json=tweet,
                    )
                )
        except Exception as exc:
            result.errors.append(f"X Crypto Search: {exc}")
        return result


class XKeyAccountsCollector(BaseHotFeedCollector):
    async def fetch(self, source_type: str | None = None, keyword: str | None = None) -> HotCollectorResult:
        result = HotCollectorResult()
        if source_type and source_type != "x_key_accounts":
            return result
        source = next((item for item in self.sources if item.get("type") == "x_key_accounts"), None)
        if not source or not source.get("enabled", False):
            return result
        if not settings.x_bearer_token:
            result.errors.append("X API 未配置，已跳过 X 重点账号采集")
            return result

        accounts = load_x_key_accounts()
        account_by_username = {
            str(item.get("username", "")).lower(): item
            for item in accounts
            if item.get("enabled", True)
        }
        queries = build_account_queries(accounts)
        headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}

        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            for batch_index, query in enumerate(queries, start=1):
                params = {
                    "query": query,
                    "max_results": max(10, min(self.max_items_per_source, 100)),
                    "tweet.fields": "created_at,public_metrics,author_id,lang",
                    "expansions": "author_id",
                    "user.fields": "username,name,verified",
                }
                try:
                    response = await client.get("https://api.x.com/2/tweets/search/recent", params=params)
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    reasons = {
                        401: "密钥无效或已失效",
                        403: "当前 X API 套餐无权访问 Recent Search",
                        429: "请求频率已达到 X API 限制",
                    }
                    reason = reasons.get(status, "X API 请求失败")
                    result.errors.append(f"X 重点账号批次 {batch_index}: HTTP {status}，{reason}")
                    continue
                except Exception as exc:
                    result.errors.append(f"X 重点账号批次 {batch_index}: {exc}")
                    continue

                users = {
                    str(user.get("id")): user
                    for user in data.get("includes", {}).get("users", [])
                    if user.get("id")
                }
                for tweet in data.get("data", []):
                    user = users.get(str(tweet.get("author_id")), {})
                    username = str(user.get("username") or tweet.get("author_id") or "").strip()
                    if not username:
                        continue
                    account = account_by_username.get(username.lower(), {})
                    metrics = tweet.get("public_metrics", {})
                    created_at = None
                    if tweet.get("created_at"):
                        created_at = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
                    post_id = str(tweet.get("id") or "")
                    link = (
                        f"https://x.com/{username}/status/{post_id}"
                        if post_id
                        else f"https://x.com/{username}"
                    )
                    result.items.append(
                        HotFeedItem(
                            source_name=f"X / @{username}",
                            source_type="x_key_accounts",
                            source_priority=account.get("priority", source.get("priority", "P1")),
                            title=tweet.get("text", "")[:240],
                            content=tweet.get("text", ""),
                            summary=tweet.get("text", "")[:280],
                            link=link,
                            author=username,
                            published_at=created_at,
                            language=tweet.get("lang"),
                            raw_metrics={
                                "likes": metrics.get("like_count", 0),
                                "reposts": metrics.get("retweet_count", 0),
                                "replies": metrics.get("reply_count", 0),
                                "quotes": metrics.get("quote_count", 0),
                            },
                            raw_json={**tweet, "author": user},
                        )
                    )
        return result


class LunarCrushCollector(BaseHotFeedCollector):
    async def fetch(self, source_type: str | None = None, keyword: str | None = None) -> HotCollectorResult:
        result = HotCollectorResult()
        if source_type and source_type != "lunarcrush":
            return result
        source = next((item for item in self.sources if item.get("type") == "lunarcrush"), None)
        if not source or not source.get("enabled", False):
            return result
        if not settings.lunarcrush_api_key:
            result.errors.append("LunarCrush API 未配置，已跳过社交热度源")
            return result

        headers = {"Authorization": f"Bearer {settings.lunarcrush_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=20, headers=headers) as client:
                response = await client.get("https://lunarcrush.com/api4/public/coins/list/v2")
                response.raise_for_status()
            data: dict[str, Any] = response.json()
            assets = data.get("data", [])[: self.max_items_per_source]
            for asset in assets:
                symbol = asset.get("symbol") or asset.get("s")
                name = asset.get("name") or asset.get("n") or symbol
                if keyword and keyword.lower() not in f"{symbol} {name}".lower():
                    continue
                social_score = asset.get("galaxy_score") or asset.get("social_score") or asset.get("alt_rank") or 0
                result.items.append(
                    HotFeedItem(
                        source_name=source.get("name", "LunarCrush"),
                        source_type="lunarcrush",
                        source_priority=source.get("priority", "P1"),
                        title=f"{symbol} social heat is rising" if symbol else f"{name} social heat is rising",
                        content=f"LunarCrush social heat signal for {name}.",
                        summary=f"{name} appears in LunarCrush social ranking.",
                        link=None,
                        author=None,
                        published_at=datetime.now(timezone.utc),
                        language="en",
                        raw_metrics={"social_score": social_score, "source_rank": asset.get("rank")},
                        raw_json=asset,
                    )
                )
        except Exception as exc:
            result.errors.append(f"LunarCrush: {exc}")
        return result
