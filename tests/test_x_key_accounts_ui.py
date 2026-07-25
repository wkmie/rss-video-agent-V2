from __future__ import annotations

import unittest

from streamlit.testing.v1 import AppTest


def render_x_key_accounts_for_test() -> None:
    from datetime import datetime, timezone

    import streamlit as st

    import ui.modules.information_hotspots as information_hotspots

    def fake_api_request(method: str, path: str, **kwargs):
        if method == "POST" and path == "/api/web3-hot/fetch-now":
            st.session_state["test.x.fetch_calls"] = st.session_state.get("test.x.fetch_calls", 0) + 1
            return {
                "fetched_count": 1,
                "inserted_count": 1,
                "updated_count": 0,
                "skipped_count": 0,
                "errors": [],
            }
        if method == "GET" and path == "/api/web3-hot/list":
            return {
                "items": [
                    {
                        "id": 1,
                        "source_name": "X / @blknoiz06",
                        "source_type": "x_key_accounts",
                        "title": "BTC liquidity is changing.",
                        "content": "BTC liquidity is changing.",
                        "link": "https://x.com/blknoiz06/status/12345",
                        "author": "blknoiz06",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "raw_metrics": {"likes": 12, "reposts": 4, "replies": 3, "quotes": 2},
                        "heat_score": 72.5,
                    }
                ]
            }
        raise AssertionError(f"Unexpected API call: {method} {path}")

    information_hotspots.api_request = fake_api_request
    information_hotspots._x_key_accounts()


def render_x_messages_for_test() -> None:
    import streamlit as st

    import ui.modules.information_hotspots as information_hotspots

    def fake_api_request(method: str, path: str, **kwargs):
        if method == "POST" and path == "/api/web3-hot/fetch-now":
            st.session_state["test.x.lazy_fetch_calls"] = (
                st.session_state.get("test.x.lazy_fetch_calls", 0) + 1
            )
            return {
                "fetched_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
                "skipped_count": 0,
                "errors": [],
            }
        if method == "GET" and path == "/api/web3-hot/list":
            return {"items": []}
        raise AssertionError(f"Unexpected API call: {method} {path}")

    information_hotspots.api_request = fake_api_request
    information_hotspots._x_messages()


class XKeyAccountsUITests(unittest.TestCase):
    def test_x_collection_waits_until_key_accounts_view_is_selected(self) -> None:
        app = AppTest.from_function(render_x_messages_for_test, default_timeout=10).run()

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.filtered_state.get("test.x.lazy_fetch_calls", 0), 0)
        self.assertEqual(app.radio[0].options, ["链接或正文录入", "重点账号采集"])

        app.radio[0].set_value("重点账号采集").run()
        self.assertEqual(app.session_state["test.x.lazy_fetch_calls"], 1)

        app.run()
        self.assertEqual(app.session_state["test.x.lazy_fetch_calls"], 1)

    def test_auto_fetch_runs_once_and_manual_refresh_runs_again(self) -> None:
        app = AppTest.from_function(render_x_key_accounts_for_test, default_timeout=10).run()

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test.x.fetch_calls"], 1)
        self.assertEqual(app.button[0].label, "抓取最新推文")
        self.assertFalse(app.button[0].disabled)

        app.run()
        self.assertEqual(app.session_state["test.x.fetch_calls"], 1)

        app.button[0].click().run()
        self.assertEqual(app.session_state["test.x.fetch_calls"], 2)

        rendered_text = "\n".join(
            [item.value for item in app.markdown]
            + [item.value for item in app.caption]
            + [item.value for item in app.text]
        )
        self.assertTrue(any("@blknoiz06" in item.label for item in app.expander))
        self.assertIn("BTC liquidity is changing.", rendered_text)
        self.assertIn("点赞 12", rendered_text)
        self.assertIn("转发 4", rendered_text)
        self.assertIn("回复 3", rendered_text)
        self.assertIn("引用 2", rendered_text)
        self.assertIn("https://x.com/blknoiz06/status/12345", rendered_text)


if __name__ == "__main__":
    unittest.main()
