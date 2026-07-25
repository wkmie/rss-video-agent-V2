from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.core.bootstrap import configure_environment


st.set_page_config(
    page_title="Web3 内容增长工作台",
    page_icon="W3",
    layout="wide",
    initial_sidebar_state="expanded",
)
configure_environment()

from ui.auth import require_login
from ui.components.layout import apply_workbench_style
from ui.core.access import is_system_admin
from ui.core.state import initialize_workbench_state
from ui.modules.content_production import render_content_production
from ui.modules.events_topics import render_events_topics
from ui.modules.information_hotspots import render_information_hotspots
from ui.modules.performance_review import render_performance_review
from ui.modules.review_publish import render_review_publish
from ui.modules.system_management import render_system_management


initialize_workbench_state()
apply_workbench_style()

language = st.session_state.get("language", "zh")
selected_language = st.sidebar.selectbox(
    "语言 / Language",
    ["zh", "en"],
    index=["zh", "en"].index(language) if language in {"zh", "en"} else 0,
    format_func=lambda value: "中文" if value == "zh" else "English",
    key="workbench.sidebar_language_selector",
)
if selected_language != language:
    st.session_state["language"] = selected_language
    st.session_state["workbench.language"] = selected_language
    st.rerun()

nav_labels = {
    "zh": ["信息与热点", "事件与选题", "内容生产", "审核发布", "数据复盘", "系统管理"],
    "en": ["Intelligence", "Events & Topics", "Content Production", "Review & Publish", "Performance", "System"],
}
labels = nav_labels.get(selected_language, nav_labels["zh"])

pages = [
    st.Page(render_information_hotspots, title=labels[0], default=True),
    st.Page(render_events_topics, title=labels[1]),
    st.Page(render_content_production, title=labels[2]),
    st.Page(render_review_publish, title=labels[3]),
    st.Page(render_performance_review, title=labels[4]),
]
if is_system_admin(st.session_state.get("auth_user")):
    pages.append(st.Page(render_system_management, title=labels[5]))

navigation = st.navigation(pages, position="sidebar")
require_login()
st.sidebar.caption("Web3 内容增长工作台 V1.0")
navigation.run()
