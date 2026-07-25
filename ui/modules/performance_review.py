from __future__ import annotations

import streamlit as st

from ui.components.layout import empty_state, metric_row, page_header, structured_placeholder


def _import_data() -> None:
    left, right = st.columns([1, 1.4])
    with left:
        st.file_uploader("上传 CSV 或 Excel", type=["csv", "xlsx", "xls"], disabled=True, key="performance.upload")
        st.radio("数据类型", ["自动识别", "作品数据", "账号数据"], horizontal=True, key="performance.import.type")
        st.info("上传能力将在数据接口阶段启用；当前不会读取或保存文件。")
    with right:
        structured_placeholder(
            "字段识别与映射",
            "自动识别平台导出字段，并允许人工修正目标字段。",
            fields=["原始字段", "识别结果", "目标字段", "数据类型", "示例值", "校验状态"],
            actions=["自动识别", "保存映射", "开始导入"],
        )


def _work_data() -> None:
    metric_row([("作品数", 0, None), ("总播放", 0, None), ("平均完播率", "--", None), ("净涨粉", 0, None)])
    st.dataframe(
        [{"作品": "暂无作品数据", "平台": "-", "发布时间": "-", "播放": 0, "完播率": "-", "3秒留存": "-", "互动": 0, "涨粉": 0}],
        hide_index=True,
        use_container_width=True,
    )


def _account_data() -> None:
    metric_row([("粉丝数", 0, None), ("周期涨粉", 0, None), ("发布数", 0, None), ("互动率", "--", None)])
    st.line_chart({"粉丝": [0, 0, 0, 0], "播放": [0, 0, 0, 0]}, height=260)
    st.caption("图表为布局占位，不代表真实业务数据。")


def _content_performance() -> None:
    columns = st.columns([1, 1, 1, 2])
    columns[0].selectbox("周期", ["最近 7 天", "最近 30 天", "最近 90 天", "自定义"], key="performance.content.period")
    columns[1].selectbox("平台", ["全部平台", "抖音", "视频号", "小红书"], key="performance.content.platform")
    columns[2].selectbox("内容类型", ["全部", "热点快讯", "事件解析", "风险提醒"], key="performance.content.type")
    metric_row([("平均播放", 0, None), ("平均完播", "--", None), ("平均 3 秒留存", "--", None), ("平均互动", 0, None)])
    st.bar_chart({"播放": [0, 0, 0], "互动": [0, 0, 0]}, height=240)


def _analysis_workspace(title: str, dimensions: list[str], conclusions: list[str]) -> None:
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader(title)
        st.multiselect("分析维度", dimensions, default=dimensions[:2], key=f"performance.analysis.{title}")
        st.bar_chart({dimension: [0, 0, 0, 0] for dimension in dimensions[:2]}, height=260)
    with right:
        structured_placeholder(f"{title}自动分析结论", "基于真实历史快照输出可追溯的表现结论。", fields=conclusions, actions=["生成分析", "导出结论"])


def _topic_analysis() -> None:
    _analysis_workspace("选题表现", ["选题等级", "内容角度", "事件类型", "负责人"], ["表现最好的选题类型", "值得继续跟进的事件", "经常被否决的 AI 建议"])


def _title_analysis() -> None:
    _analysis_workspace("标题表现", ["标题版本", "关键词", "句式", "情绪强度"], ["点击表现较高的标题模式", "高风险夸张表达", "可复用标题特征"])


def _time_analysis() -> None:
    _analysis_workspace("发布时间表现", ["星期", "时段", "平台", "账号"], ["更有效的发布时间", "不同平台时间差异", "样本量提示"])


def _report() -> None:
    columns = st.columns([1, 1, 1, 2])
    columns[0].selectbox("报告周期", ["本周", "上周", "本月", "自定义"], key="performance.report.period")
    columns[1].selectbox("账号", ["全部账号"], key="performance.report.account")
    columns[2].selectbox("平台", ["全部平台", "抖音", "视频号", "小红书"], key="performance.report.platform")
    columns[3].button("生成复盘报告", type="primary", disabled=True)
    structured_placeholder(
        "周期复盘报告",
        "汇总账号增长、作品表现、选题、标题、开头留存和发布时间，并形成下周期行动建议。",
        fields=["关键结论", "最佳作品", "问题作品", "选题建议", "标题建议", "发布时间建议", "待验证假设"],
        actions=["导出报告", "反哺评分规则", "更新账号画像"],
    )


def render_performance_review() -> None:
    page_header("数据复盘", "导入发布后数据，分析作品与账号表现，并将结论反哺选题和内容生产。", stage="模拟结构")
    tabs = st.tabs(["数据导入", "作品数据", "账号数据", "内容表现", "选题分析", "标题分析", "发布时间分析", "复盘报告"])
    renderers = [_import_data, _work_data, _account_data, _content_performance, _topic_analysis, _title_analysis, _time_analysis, _report]
    for tab, renderer in zip(tabs, renderers):
        with tab:
            renderer()
