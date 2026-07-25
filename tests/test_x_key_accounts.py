from __future__ import annotations

import asyncio
import re
import unittest
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.database import Base
from app.db.models import Web3HotItem  # noqa: F401
from app.services.web3_hot_collectors.social import (
    XKeyAccountsCollector,
    build_account_queries,
    load_x_key_accounts,
)
from ui.core.api_client import _direct_request


class XKeyAccountConfigurationTests(unittest.TestCase):
    def test_configuration_loads_all_supplied_accounts(self) -> None:
        accounts = load_x_key_accounts()

        self.assertEqual(len(accounts), 45)
        self.assertEqual(len({item["username"].lower() for item in accounts}), 45)
        enabled = [item for item in accounts if item["enabled"]]
        invalid = [item for item in accounts if not item["enabled"]]
        self.assertEqual(len(enabled), 43)
        self.assertTrue(all(re.fullmatch(r"[A-Za-z0-9_]{1,15}", item["username"]) for item in enabled))
        self.assertEqual(
            {item["username"] for item in invalid},
            {"thesextheoffender", "CryptoIndiaMemes"},
        )

    def test_queries_include_each_enabled_account_once_within_limit(self) -> None:
        accounts = load_x_key_accounts()
        accounts.append(
            {
                "username": "disabled_test",
                "display_name": "",
                "region": "测试",
                "priority": "P2",
                "enabled": False,
            }
        )

        queries = build_account_queries(accounts)
        queried_usernames = [
            username
            for query in queries
            for username in re.findall(r"from:([A-Za-z0-9_]+)", query)
        ]

        expected = [item["username"] for item in accounts if item["enabled"]]
        self.assertEqual(sorted(name.lower() for name in queried_usernames), sorted(name.lower() for name in expected))
        self.assertEqual(len(queried_usernames), len(set(name.lower() for name in queried_usernames)))
        self.assertTrue(all(len(query) <= 512 for query in queries))
        self.assertTrue(all(query.endswith("-is:retweet") for query in queries))


class XKeyAccountsCollectorTests(unittest.TestCase):
    source = {
        "name": "X Key Accounts",
        "type": "x_key_accounts",
        "enabled": True,
        "priority": "P1",
    }

    def test_collector_maps_username_metrics_and_post_link(self) -> None:
        response_data = {
            "data": [
                {
                    "id": "12345",
                    "text": "BTC liquidity is changing.",
                    "author_id": "user-1",
                    "created_at": "2026-07-24T00:00:00.000Z",
                    "lang": "en",
                    "public_metrics": {
                        "like_count": 12,
                        "retweet_count": 4,
                        "reply_count": 3,
                        "quote_count": 2,
                    },
                }
            ],
            "includes": {
                "users": [
                    {
                        "id": "user-1",
                        "username": "blknoiz06",
                        "name": "Ansem",
                        "verified": True,
                    }
                ]
            },
        }

        class FakeResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return response_data

        class FakeClient:
            def __init__(self, *args, **kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args) -> None:
                return None

            async def get(self, *args, **kwargs):
                return FakeResponse()

        collector = XKeyAccountsCollector([self.source], max_items_per_source=50)
        with patch.object(settings, "x_bearer_token", "test-token"), patch(
            "app.services.web3_hot_collectors.social.httpx.AsyncClient",
            FakeClient,
        ), patch(
            "app.services.web3_hot_collectors.social.build_account_queries",
            return_value=["(from:blknoiz06) -is:retweet"],
        ):
            result = asyncio.run(collector.fetch(source_type="x_key_accounts"))

        self.assertFalse(result.errors)
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertEqual(item.author, "blknoiz06")
        self.assertEqual(item.source_name, "X / @blknoiz06")
        self.assertEqual(item.link, "https://x.com/blknoiz06/status/12345")
        self.assertEqual(item.raw_metrics["likes"], 12)
        self.assertEqual(item.raw_metrics["reposts"], 4)
        self.assertEqual(item.raw_metrics["replies"], 3)
        self.assertEqual(item.raw_metrics["quotes"], 2)

    def test_collector_continues_after_one_query_batch_fails(self) -> None:
        success_data = {
            "data": [{"id": "99", "text": "ETH update", "author_id": "user-2", "public_metrics": {}}],
            "includes": {"users": [{"id": "user-2", "username": "Poe_Ether", "name": "Poe"}]},
        }

        class FakeResponse:
            def __init__(self, status_code: int, data: dict) -> None:
                self.status_code = status_code
                self._data = data

            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    request = httpx.Request("GET", "https://api.x.com/2/tweets/search/recent")
                    response = httpx.Response(self.status_code, request=request)
                    raise httpx.HTTPStatusError("request failed", request=request, response=response)

            def json(self) -> dict:
                return self._data

        class FakeClient:
            call_count = 0

            def __init__(self, *args, **kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args) -> None:
                return None

            async def get(self, *args, **kwargs):
                type(self).call_count += 1
                if type(self).call_count == 1:
                    return FakeResponse(429, {})
                return FakeResponse(200, success_data)

        collector = XKeyAccountsCollector([self.source], max_items_per_source=50)
        with patch.object(settings, "x_bearer_token", "test-token"), patch(
            "app.services.web3_hot_collectors.social.httpx.AsyncClient",
            FakeClient,
        ), patch(
            "app.services.web3_hot_collectors.social.build_account_queries",
            return_value=["(from:first) -is:retweet", "(from:Poe_Ether) -is:retweet"],
        ):
            result = asyncio.run(collector.fetch(source_type="x_key_accounts"))

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].author, "Poe_Ether")
        self.assertEqual(len(result.errors), 1)
        self.assertIn("429", result.errors[0])


class XKeyAccountsDirectAPITests(unittest.TestCase):
    def test_unified_api_client_lists_key_account_posts_in_direct_mode(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        try:
            with patch("ui.core.api_client._session_factory", return_value=session_factory):
                result = _direct_request(
                    "GET",
                    "/api/web3-hot/list",
                    None,
                    {
                        "source_type": "x_key_accounts",
                        "hours": 24,
                        "limit": 100,
                    },
                )
        finally:
            Base.metadata.drop_all(engine)
            engine.dispose()

        self.assertEqual(result, {"items": []})


if __name__ == "__main__":
    unittest.main()
