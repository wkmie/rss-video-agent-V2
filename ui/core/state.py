from __future__ import annotations

import streamlit as st


DEFAULT_STATE = {
    "language": "zh",
    "workbench.language": "zh",
    "workbench.selected_message_id": None,
    "workbench.selected_event_id": None,
    "workbench.selected_topic_id": None,
    "workbench.selected_content_id": None,
    "workbench.notice": None,
    "workbench.filters": {},
    "rss.articles": [],
    "rss.selected_article_id": None,
    "rss.fetch_result": None,
    "rss.analyses": {},
    "content.section": "内容工作台",
    "content.article.result": "",
    "content.article.result_article_id": None,
    "content.trading.result": "",
    "content.trading.matches": [],
    "content.trading.source_notice": "",
    "content.trading.source_name": "",
    "info.x.accounts.auto_fetch_attempted": False,
    "info.x.accounts.fetch_result": None,
    "info.x.accounts.items": [],
}


def initialize_workbench_state() -> None:
    for key, value in DEFAULT_STATE.items():
        st.session_state.setdefault(key, value)

    st.session_state["workbench.language"] = st.session_state.get("language", "zh")
