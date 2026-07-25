from __future__ import annotations

import streamlit as st

from ui.components.layout import empty_state, filter_bar, metric_row, page_header, structured_placeholder, workflow


TOPIC_STATUSES = ["全部状态", "待判断", "观察中", "已入选", "调查中", "制作中", "待审核", "已发布", "已复盘", "已放弃"]


def _event_center() -> None:
    metric_row([("待判断事件", 24, "+6"), ("持续发酵", 8, "+2"), ("高可信事件", 11, None), ("来源冲突", 3, None)])
    filter_bar(
        key_prefix="topics.events",
        categories=["全部", "市场", "监管", "安全", "AI 科技", "人物"],
        sources=["全部来源", "RSS 聚合", "X 聚合", "事件日历", "人工录入"],
        statuses=TOPIC_STATUSES,
    )
    st.dataframe(
        [
            {"事件": "多个来源讨论同一行业变化", "来源数": 5, "可信度": "待核验", "生命周期": "上升期", "热度": 84, "状态": "待判断"},
            {"事件": "未来政策窗口临近", "来源数": 3, "可信度": "中", "生命周期": "预热期", "热度": 73, "状态": "观察中"},
        ],
        use_container_width=True,
        hide_index=True,
    )
    structured_placeholder("事件详情", "聚合来源、事件时间线、可信度、热度变化和来源冲突。", actions=["AI 初评", "继续调查", "加入选题库"])


def _ai_evaluation() -> None:
    metric_row([("S 级", 2, None), ("A 级", 7, None), ("建议调查", 13, None), ("来源不足", 5, None)])
    selected = st.selectbox("待评估事件", ["请选择事件", "多个来源讨论同一行业变化", "未来政策窗口临近"], key="topics.ai.event")
    left, right = st.columns([1, 2.4])
    with left:
        with st.container(border=True):
            st.metric("AI 等级", "A")
            st.metric("综合分数", "82 / 100")
            st.write("是否值得调查：**是**")
            st.write("可靠来源：**仍需补充**")
    with right:
        st.text_area("判断理由", "当前为页面结构示例；接入现有新闻分析后显示真实判断。", height=90, disabled=True)
        cols = st.columns(3)
        cols[0].text_input("建议内容角度", "事件解析", disabled=True)
        cols[1].text_input("最佳内容形式", "短视频口播", disabled=True)
        cols[2].text_input("建议发布时间", "事件确认后 2 小时内", disabled=True)
        st.text_area("风险提示", "来源与关键数字需人工核验。", height=70, disabled=True)
    st.button("执行 AI 初评", type="primary", disabled=selected == "请选择事件")


def _investigation() -> None:
    columns = st.columns([2, 1, 1, 1])
    columns[0].selectbox("调查事件", ["请选择事件", "多个来源讨论同一行业变化"], key="topics.investigation.event")
    columns[1].selectbox("负责人", ["未指派", "当前用户"], key="topics.investigation.owner")
    columns[2].selectbox("优先级", ["普通", "高", "紧急"], key="topics.investigation.priority")
    columns[3].date_input("截止时间", key="topics.investigation.deadline")
    structured_placeholder(
        "人工侦察记录",
        "记录事实核验、补充来源、关键数字、争议点和编辑判断。",
        fields=["调查结论", "补充来源", "关键数字", "来源冲突", "编辑备注"],
        actions=["保留", "继续调查", "加入选题库", "标记噪音"],
    )


def _topic_library() -> None:
    filter_bar(
        key_prefix="topics.library",
        categories=["全部", "Web3", "AI", "科技", "安全"],
        sources=["全部来源", "实时热点", "事前事件", "人工选题"],
        statuses=TOPIC_STATUSES,
    )
    st.dataframe(
        [{"选题": "暂无已确认选题", "等级": "-", "角度": "-", "负责人": "-", "优先级": "-", "截止时间": "-", "状态": "待判断"}],
        hide_index=True,
        use_container_width=True,
    )
    actions = st.columns([1, 1, 1, 1, 3])
    for column, label in zip(actions, ["新建选题", "指派负责人", "设置优先级", "进入制作"]):
        column.button(label, disabled=True, use_container_width=True)


def _pre_topics() -> None:
    metric_row([("未来事件", 0, None), ("待生成", 0, None), ("已审核", 0, None), ("已发布", 0, None)])
    structured_placeholder(
        "事前选题工作区",
        "接入现有自动事前选题生成、平台和时长选择、补充要求及状态管理。",
        fields=["事件信息", "目标平台", "视频时长", "补充要求", "生成结果"],
        actions=["生成事前选题", "标记已审核", "标记已发布", "放弃"],
        status="已有能力待接入",
    )


def _board() -> None:
    metric_row([("本周选题", 0, None), ("制作中", 0, None), ("待审核", 0, None), ("已逾期", 0, None)])
    workflow(["待判断", "观察中", "已入选", "调查中", "制作中", "待审核", "已发布", "已复盘"], active_index=0)
    st.write("")
    columns = st.columns(4)
    for column, title in zip(columns, ["待判断", "调查中", "制作中", "待审核"]):
        with column.container(border=True):
            st.markdown(f"**{title}**")
            st.caption("暂无任务")


def render_events_topics() -> None:
    page_header("事件与选题", "完成事件归并、AI 初评、人工侦察、事前布局和选题状态管理。")
    tabs = st.tabs(["事件中心", "AI 初评", "人工侦察", "选题库", "事前选题", "任务看板"])
    renderers = [_event_center, _ai_evaluation, _investigation, _topic_library, _pre_topics, _board]
    for tab, renderer in zip(tabs, renderers):
        with tab:
            renderer()
