from __future__ import annotations

import streamlit as st

from ui.components.layout import empty_state, metric_row, page_header, structured_placeholder


REVIEW_ITEMS = [
    "事实是否准确",
    "是否存在未确认信息",
    "数字是否有来源",
    "是否包含投资建议",
    "标题是否夸大",
    "平台敏感词",
    "视频是否完整",
    "封面是否完整",
    "标签是否完整",
    "字幕是否完整",
]


def _review_queue() -> None:
    metric_row([("待审核", 0, None), ("今日通过", 0, None), ("需修改", 0, None), ("超时", 0, None)])
    columns = st.columns([2, 1, 1, 1])
    columns[0].text_input("搜索内容", placeholder="标题、选题或负责人", key="review.queue.search")
    columns[1].selectbox("内容类型", ["全部", "热点快讯", "事件解析", "交易认知"], key="review.queue.type")
    columns[2].selectbox("负责人", ["全部", "当前用户", "未指派"], key="review.queue.owner")
    columns[3].selectbox("状态", ["待审核", "需修改", "已通过"], key="review.queue.status")
    st.dataframe([{"内容": "暂无待审核内容", "类型": "-", "版本": "-", "提交人": "-", "提交时间": "-", "状态": "-"}], hide_index=True, use_container_width=True)


def _script_review() -> None:
    left, right = st.columns([1.8, 1])
    with left:
        empty_state("尚未选择待审核文案", "从待审核内容列表中选择一个内容版本。")
        st.text_area("审核意见", placeholder="记录需要修改的事实、表达或平台风险", height=120, key="review.script.comment")
    with right:
        with st.container(border=True):
            st.markdown("**审核清单**")
            for index, item in enumerate(REVIEW_ITEMS[:6]):
                st.checkbox(item, key=f"review.script.check.{index}", disabled=True)
        actions = st.columns(2)
        actions[0].button("退回修改", disabled=True, use_container_width=True)
        actions[1].button("审核通过", type="primary", disabled=True, use_container_width=True)


def _video_review() -> None:
    left, right = st.columns([2, 1])
    with left:
        structured_placeholder("成片预览", "预留视频播放器、封面预览、字幕预览和基础媒体信息。", fields=["视频", "封面", "字幕", "分辨率", "时长"])
    with right:
        with st.container(border=True):
            st.markdown("**完整性检查**")
            for index, item in enumerate(REVIEW_ITEMS[6:]):
                st.checkbox(item, key=f"review.video.check.{index}", disabled=True)
        st.button("提交成片审核结果", disabled=True, use_container_width=True)


def _package() -> None:
    structured_placeholder(
        "标准发布包",
        "生成不依赖模拟点击的标准交付包，供运营人工发布。",
        fields=["视频", "封面", "标题", "标签", "简介", "发布时间建议", "字幕", "一键复制内容"],
        actions=["生成发布包", "下载 ZIP", "复制发布信息"],
    )


def _scheduled() -> None:
    columns = st.columns([2, 1, 1, 1])
    columns[0].selectbox("已审核内容", ["请选择内容"], key="review.schedule.content")
    columns[1].selectbox("发布平台", ["抖音", "视频号", "小红书", "TikTok", "YouTube Shorts"], key="review.schedule.platform")
    columns[2].date_input("发布日期", key="review.schedule.date")
    columns[3].time_input("发布时间", key="review.schedule.time")
    st.button("创建定时发布任务", type="primary", disabled=True)
    st.info("只有具备稳定官方发布接口的平台才会接入自动发布；其他平台使用标准发布包。")


def _records() -> None:
    metric_row([("本周发布", 0, None), ("发布成功", 0, None), ("发布失败", 0, None), ("待同步数据", 0, None)])
    st.dataframe([{"内容": "暂无发布记录", "平台": "-", "账号": "-", "发布时间": "-", "发布链接": "-", "状态": "-"}], hide_index=True, use_container_width=True)


def _failed() -> None:
    empty_state("没有失败任务", "失败发布任务将在此展示错误原因、重试次数和处理建议。")
    structured_placeholder("失败处理", "支持查看错误、重新生成发布包和对官方接口任务进行安全重试。", actions=["查看错误", "重试任务", "转人工处理"])


def render_review_publish() -> None:
    page_header("审核发布", "完成事实与平台风险审核，生成标准发布包，并管理发布任务和记录。", stage="页面结构已就绪")
    tabs = st.tabs(["待审核内容", "文案审核", "成片审核", "发布包", "定时发布", "发布记录", "失败任务"])
    renderers = [_review_queue, _script_review, _video_review, _package, _scheduled, _records, _failed]
    for tab, renderer in zip(tabs, renderers):
        with tab:
            renderer()
