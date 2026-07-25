from __future__ import annotations

from collections.abc import Iterable, Sequence

import streamlit as st


def apply_workbench_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.7rem; padding-bottom: 3rem; max-width: 1500px;}
        [data-testid="stSidebar"] {border-right: 1px solid #e5e7eb;}
        [data-testid="stMetric"] {border: 1px solid #e5e7eb; padding: 12px 14px; border-radius: 6px;}
        [data-testid="stMetricLabel"] {font-weight: 600;}
        div[data-testid="stVerticalBlockBorderWrapper"] {border-color: #e5e7eb; border-radius: 6px;}
        .wb-eyebrow {font-size: .78rem; font-weight: 700; color: #2563eb; margin-bottom: .25rem;}
        .wb-status {display: inline-block; border: 1px solid #cbd5e1; border-radius: 999px; padding: 2px 8px; font-size: .75rem; color: #475569;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, description: str, *, stage: str = "框架已就绪") -> None:
    left, right = st.columns([6, 1])
    with left:
        st.markdown('<div class="wb-eyebrow">WEB3 CONTENT GROWTH</div>', unsafe_allow_html=True)
        st.title(title)
        st.caption(description)
    with right:
        st.markdown(f'<div class="wb-status">{stage}</div>', unsafe_allow_html=True)
    st.divider()


def metric_row(metrics: Sequence[tuple[str, str | int, str | None]]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value, delta) in zip(columns, metrics):
        column.metric(label, value, delta=delta)


def filter_bar(
    *,
    key_prefix: str,
    categories: Sequence[str],
    sources: Sequence[str],
    statuses: Sequence[str],
) -> dict[str, str]:
    columns = st.columns([2.2, 1.2, 1.2, 1.2, 1.2])
    search = columns[0].text_input("搜索", placeholder="标题、关键词或来源", key=f"{key_prefix}.search")
    category = columns[1].selectbox("分类", categories, key=f"{key_prefix}.category")
    source = columns[2].selectbox("来源", sources, key=f"{key_prefix}.source")
    time_range = columns[3].selectbox(
        "时间", ["最近 6 小时", "最近 24 小时", "最近 7 天", "全部"], key=f"{key_prefix}.time"
    )
    status = columns[4].selectbox("状态", statuses, key=f"{key_prefix}.status")
    return {"search": search, "category": category, "source": source, "time_range": time_range, "status": status}


def section_title(title: str, description: str | None = None) -> None:
    st.subheader(title)
    if description:
        st.caption(description)


def structured_placeholder(
    title: str,
    description: str,
    *,
    fields: Iterable[str] = (),
    actions: Iterable[str] = (),
    status: str = "尚未实现",
) -> None:
    with st.container(border=True):
        top, badge = st.columns([5, 1])
        top.markdown(f"**{title}**")
        top.caption(description)
        badge.markdown(f'<div class="wb-status">{status}</div>', unsafe_allow_html=True)
        field_values = list(fields)
        if field_values:
            st.write(" · ".join(field_values))
        action_values = list(actions)
        if action_values:
            columns = st.columns(min(len(action_values), 4))
            for index, action in enumerate(action_values):
                columns[index % len(columns)].button(
                    action,
                    key=f"placeholder.{title}.{index}",
                    disabled=True,
                    use_container_width=True,
                )


def workflow(steps: Sequence[str], active_index: int = 0) -> None:
    columns = st.columns(len(steps))
    for index, (column, step) in enumerate(zip(columns, steps)):
        state = "进行中" if index == active_index else "待处理"
        column.markdown(f"**{index + 1}. {step}**")
        column.caption(state)


def empty_state(title: str, description: str, action: str | None = None) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(description)
        if action:
            st.button(action, disabled=True, key=f"empty.{title}")
