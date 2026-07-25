from __future__ import annotations

import json

import streamlit as st

from ui.components.layout import empty_state, metric_row, page_header, structured_placeholder, workflow
from ui.core.api_client import api_request
from app.services.title_translation import is_effective_chinese


ANGLES = ["热点快讯", "事件解析", "争议观点", "普通人科普", "风险提醒", "人物故事", "行业影响", "市场情绪"]
PLATFORMS = ["抖音", "视频号", "小红书", "TikTok", "YouTube Shorts"]
DURATIONS = ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"]
SECTIONS = ["内容工作台", "文章生成文案", "主题直写", "交易认知", "内容版本", "分镜与素材", "内容模板"]


def _article_title(article: dict) -> str:
    if is_effective_chinese(article.get("title_zh")):
        return str(article["title_zh"])
    if is_effective_chinese(article.get("title")):
        return str(article["title"])
    return f"文章 #{article.get('id')}（中文标题翻译中）"


def _selected_article() -> tuple[dict | None, list[dict]]:
    articles = list(st.session_state.get("rss.articles") or st.session_state.get("articles") or [])
    selected_id = st.session_state.get("rss.selected_article_id") or st.session_state.get("selected_article_id")
    if not selected_id:
        return None, articles

    selected = next((item for item in articles if int(item["id"]) == int(selected_id)), None)
    if selected:
        return selected, articles

    try:
        items = api_request(
            "GET",
            "/api/news/list",
            params={"limit": 200},
            timeout=60,
        ).get("items", [])
    except Exception:
        return None, articles
    st.session_state["rss.articles"] = items
    selected = next((item for item in items if int(item["id"]) == int(selected_id)), None)
    return selected, items


def _parse_content_package(value: str) -> dict | None:
    try:
        package = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    required = {"video_titles", "cover_titles", "video_tags", "script"}
    return package if isinstance(package, dict) and required.issubset(package) else None


def _render_generation_result(value: str, article_id: int) -> None:
    package = _parse_content_package(value)
    st.subheader("生成结果")
    if not package:
        st.text_area("视频文案", value, height=560, key=f"content.article.plain_result.{article_id}")
        st.download_button(
            "下载文案 TXT",
            value,
            file_name=f"article_script_{article_id}.txt",
            mime="text/plain",
            key=f"content.article.download_plain.{article_id}",
        )
        return

    title_column, cover_column = st.columns(2)
    with title_column:
        st.markdown("**视频标题**")
        for title in package.get("video_titles", []):
            st.write(f"- {title}")
    with cover_column:
        st.markdown("**封面标题**")
        for title in package.get("cover_titles", []):
            st.write(f"- {title}")
    st.markdown("**视频标签**")
    st.write(" ".join(str(tag) for tag in package.get("video_tags", [])))
    st.text_area(
        "完整口播文案",
        str(package.get("script", "")),
        height=520,
        key=f"content.article.package_result.{article_id}",
    )
    st.download_button(
        "下载内容包 JSON",
        value,
        file_name=f"article_content_package_{article_id}.json",
        mime="application/json",
        key=f"content.article.download_package.{article_id}",
    )


def _workspace() -> None:
    selected, _ = _selected_article()
    metric_row(
        [
            ("待生产素材", 1 if selected else 0, None),
            ("草稿", 1 if st.session_state.get("content.article.result") else 0, None),
            ("待审核", 0, None),
            ("本周完成", 0, None),
        ]
    )
    workflow(["素材分析", "叙事角度", "标题与封面", "脚本生成", "人工修改", "审核", "分镜与素材交付"], active_index=0)
    st.write("")
    if selected:
        with st.container(border=True):
            selected_body, selected_action = st.columns([5, 1.4])
            selected_body.markdown(f"**待生产素材：{_article_title(selected)}**")
            selected_body.caption(
                f"{selected.get('source_name', '-')} · {selected.get('published_at') or '时间未知'} · "
                f"热度 {float(selected.get('score') or 0):.0f}/100"
            )
            if selected_action.button(
                "开始生成文案",
                type="primary",
                use_container_width=True,
                key="content.workspace.open_article",
            ):
                st.session_state["content.section"] = "文章生成文案"
                st.rerun()
    else:
        empty_state(
            "暂无待生产素材",
            "请先到“信息与热点中心 → RSS / Atom”选择一篇文章。",
        )

    left, right = st.columns([1.15, 2])
    with left:
        st.selectbox("已确认选题", ["请选择选题"], key="content.workspace.topic")
        st.multiselect("内容角度", ANGLES, default=["事件解析"], key="content.workspace.angles")
        cols = st.columns(2)
        cols[0].selectbox("目标平台", ["抖音", "视频号", "小红书", "TikTok", "YouTube Shorts"], key="content.workspace.platform")
        cols[1].selectbox("视频时长", ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"], index=2, key="content.workspace.duration")
        st.text_area("补充要求", placeholder="目标受众、表达风格、风险边界", key="content.workspace.instruction")
        st.button("开始内容生产", type="primary", disabled=True, use_container_width=True)
    with right:
        structured_placeholder(
            "内容交付区",
            "统一承载标题、封面标题、标签、事件摘要、核验说明、口播文案和素材交付。",
            fields=["3 个视频标题", "3 个封面标题", "8-15 个标签", "事件摘要", "信息核验", "完整口播"],
            actions=["局部改写", "保存版本", "提交审核"],
        )


def _article_script() -> None:
    selected, articles = _selected_article()
    if not selected:
        empty_state(
            "尚未选择 RSS 文章",
            "请先进入“信息与热点中心 → RSS / Atom”，点击目标消息右侧的“选择文章”。",
        )
        return

    article_ids = [int(item["id"]) for item in articles]
    selected_id = int(selected["id"])
    if selected_id not in article_ids:
        articles = [selected, *articles]
        article_ids = [int(item["id"]) for item in articles]

    chosen = st.selectbox(
        "当前 RSS 素材",
        articles,
        index=article_ids.index(selected_id),
        format_func=lambda article: f"#{article['id']} · {_article_title(article)}",
        key="content.article.source",
    )
    chosen_id = int(chosen["id"])
    if chosen_id != selected_id:
        st.session_state["rss.selected_article_id"] = chosen_id
        st.session_state["selected_article_id"] = chosen_id
        st.session_state["workbench.selected_message_id"] = chosen_id
        st.session_state["content.article.result"] = ""
        st.session_state["content.article.result_article_id"] = None
        selected = chosen
        selected_id = chosen_id

    with st.container(border=True):
        article_body, article_score = st.columns([5, 1])
        article_body.markdown(f"### {_article_title(selected)}")
        if (
            is_effective_chinese(selected.get("title_zh"))
            and selected.get("title")
            and selected["title_zh"] != selected["title"]
        ):
            article_body.caption(selected["title"])
        article_body.caption(
            f"{selected.get('source_name', '-')} · {selected.get('category', '-')} · "
            f"{selected.get('published_at') or '时间未知'}"
        )
        if selected.get("summary"):
            article_body.write(selected["summary"])
        if selected.get("link"):
            article_body.markdown(f"[查看原文]({selected['link']})")
        article_score.metric("热度", f"{float(selected.get('score') or 0):.0f}/100")

    left, right = st.columns([1.05, 1.95])
    with left:
        mode = st.radio(
            "生成方式",
            ["默认文案生成", "自定义提示词生成"],
            key="content.article.mode",
        )
        platform = st.selectbox("发布平台", PLATFORMS, key="content.article.platform")
        duration = st.selectbox("视频时长", DURATIONS, index=2, key="content.article.duration")
        use_llm = st.toggle(
            "使用大模型生成",
            value=True,
            key="content.article.use_llm",
            help="关闭后使用本地规则版，可用于离线验证。",
        )
        custom_prompt = ""
        if mode == "自定义提示词生成":
            st.caption("不包含视频标题、视频标签，如有需要请输入特定提示词")
            custom_prompt = st.text_area(
                "自定义提示词",
                height=180,
                placeholder="请描述文案结构、风格、目标受众和输出要求。",
                key="content.article.prompt",
            )

        generate_disabled = mode == "自定义提示词生成" and not custom_prompt.strip()
        if st.button(
            "生成文章内容包" if mode == "默认文案生成" else "按自定义提示词生成",
            type="primary",
            disabled=generate_disabled,
            use_container_width=True,
            key="content.article.generate",
        ):
            with st.spinner("正在根据所选文章生成内容..."):
                try:
                    result = api_request(
                        "POST",
                        "/api/script/from_article",
                        payload={
                            "article_id": selected_id,
                            "duration": duration,
                            "platform": platform,
                            "use_llm": use_llm,
                            "custom_prompt": custom_prompt.strip(),
                        },
                        timeout=240,
                    )
                    st.session_state["content.article.result"] = result["script_text"]
                    st.session_state["content.article.result_article_id"] = selected_id
                except Exception as exc:
                    st.error(f"生成失败：{exc}")

    with right:
        result_text = st.session_state.get("content.article.result", "")
        result_article_id = st.session_state.get("content.article.result_article_id")
        if result_text and int(result_article_id or 0) == selected_id:
            _render_generation_result(result_text, selected_id)
        else:
            structured_placeholder(
                "文章内容包",
                "生成后在此展示 3 个视频标题、3 个封面标题、视频标签和完整口播文案。",
                fields=["视频标题", "封面标题", "视频标签", "完整口播文案"],
                status="等待生成",
            )


def _topic_writer() -> None:
    left, right = st.columns([1.1, 2])
    with left:
        st.text_area("输入主题", height=130, placeholder="输入准备制作的视频主题", key="content.topic.input")
        st.selectbox("内容角度", ANGLES, key="content.topic.angle")
        cols = st.columns(2)
        cols[0].selectbox("平台", ["抖音", "视频号", "小红书", "TikTok", "YouTube Shorts"], key="content.topic.platform")
        cols[1].selectbox("时长", ["30秒", "1分钟", "3分钟", "5分钟", "10分钟"], index=2, key="content.topic.duration")
        st.text_area("自定义提示词（可选）", key="content.topic.prompt")
        st.button("生成主题内容包", type="primary", disabled=True, use_container_width=True)
    with right:
        structured_placeholder("主题直写结果", "接入原主题直写的默认提示词和纯自定义提示词两种模式。", fields=["标题", "封面", "标签", "口播文案"], actions=["重新生成", "下载 TXT", "保存草稿"], status="已有能力待接入")


def _trading() -> None:
    st.caption(
        "从“尼克｜交易性格”公开内容蒸馏出的认知库中检索相关依据，再生成交易认知口播。"
    )
    st.warning("交易认知内容只提供教育性认知，不提供具体品种、点位、买卖信号或收益承诺。")
    left, right = st.columns([1.1, 2])
    with left:
        question = st.text_area(
            "输入交易认知问题",
            height=130,
            placeholder="例如：交易为什么要设置止损？",
            key="content.trading.question",
        )
        cols = st.columns(2)
        platform = cols[0].selectbox("发布平台", PLATFORMS, key="content.trading.platform")
        duration = cols[1].selectbox(
            "视频时长",
            DURATIONS,
            index=1,
            key="content.trading.duration",
        )
        use_llm = st.toggle(
            "使用大模型生成",
            value=True,
            key="content.trading.llm",
            help="关闭后使用本地规则版，可用于离线验证。",
        )
        if st.button(
            "生成交易认知文案",
            type="primary",
            use_container_width=True,
            key="content.trading.generate",
        ):
            if not question.strip():
                st.warning("请先输入交易认知问题。")
            else:
                with st.spinner("正在检索认知资料并生成文案..."):
                    try:
                        result = api_request(
                            "POST",
                            "/api/trading-cognition/generate",
                            payload={
                                "question": question.strip(),
                                "duration": duration,
                                "platform": platform,
                                "use_llm": use_llm,
                                "knowledge_limit": 4,
                            },
                            timeout=240,
                        )
                        st.session_state["content.trading.result"] = result["script_text"]
                        st.session_state["content.trading.matches"] = result.get("matched_knowledge", [])
                        st.session_state["content.trading.source_notice"] = result.get("source_notice", "")
                        st.session_state["content.trading.source_name"] = result.get("source_name", "")
                    except Exception as exc:
                        st.error(f"生成失败：{exc}")
    with right:
        result_text = st.session_state.get("content.trading.result", "")
        if result_text:
            package = _parse_content_package(result_text)
            st.subheader("生成结果")
            if package:
                title_column, cover_column = st.columns(2)
                with title_column:
                    st.markdown("**视频标题**")
                    for title in package.get("video_titles", []):
                        st.write(f"- {title}")
                with cover_column:
                    st.markdown("**封面标题**")
                    for title in package.get("cover_titles", []):
                        st.write(f"- {title}")

                tags = package.get("video_tags", [])
                if tags:
                    st.markdown("**视频标签**")
                    st.write(" ".join(str(tag) for tag in tags))
                st.text_area(
                    "完整口播文案",
                    str(package.get("script", "")),
                    height=520,
                    key="content.trading.package_result",
                )
                st.download_button(
                    "下载内容包 JSON",
                    result_text,
                    file_name="trading_cognition_content_package.json",
                    mime="application/json",
                    key="content.trading.download_package",
                )
            else:
                st.text_area(
                    "生成结果",
                    result_text,
                    height=640,
                    key="content.trading.plain_result",
                )
                st.download_button(
                    "下载 TXT",
                    result_text,
                    file_name="trading_cognition_content_package.txt",
                    mime="text/plain",
                    key="content.trading.download_plain",
                )

            source_name = st.session_state.get("content.trading.source_name", "")
            source_notice = st.session_state.get("content.trading.source_notice", "")
            if source_name:
                st.markdown(f"**认知来源：{source_name}**")
            if source_notice:
                st.caption(f"资料来源说明：{source_notice}")

            matches = st.session_state.get("content.trading.matches", [])
            if matches:
                with st.expander("本次采用的认知依据"):
                    for card in matches:
                        st.markdown(f"**{card.get('title', '')}**")
                        st.write(card.get("belief", ""))
                        if card.get("action_rule"):
                            st.caption(card["action_rule"])
        else:
            structured_placeholder(
                "认知检索与生成结果",
                "展示命中的认知依据、来源说明和结构化内容包。",
                fields=["认知依据", "来源说明", "视频标题", "封面标题", "视频标签", "口播文案"],
                status="等待生成",
            )


def _versions() -> None:
    st.dataframe([{"版本": "暂无内容版本", "内容": "-", "修改人": "-", "修改说明": "-", "创建时间": "-", "状态": "-"}], hide_index=True, use_container_width=True)
    structured_placeholder("版本对比", "选择两个版本后展示差异，并支持恢复和创建新版本。", actions=["对比版本", "恢复版本", "创建副本"])


def _storyboard() -> None:
    structured_placeholder(
        "分镜与素材交付",
        "将审核前文案拆分为镜头、画面、字幕、时长和素材关键词。",
        fields=["镜头序号", "口播段落", "画面描述", "素材关键词", "字幕", "预计时长"],
        actions=["自动生成分镜", "导出字幕", "提词器版本", "生成封面方案"],
    )


def _templates() -> None:
    st.dataframe(
        [
            {"模板": "热点快讯", "适用平台": "抖音 / 视频号", "默认时长": "1分钟", "状态": "系统预置"},
            {"模板": "事件解析", "适用平台": "全平台", "默认时长": "3分钟", "状态": "系统预置"},
            {"模板": "风险提醒", "适用平台": "全平台", "默认时长": "1分钟", "状态": "系统预置"},
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.button("新建内容模板", disabled=True)


def render_content_production() -> None:
    page_header("内容生产", "让人工确认的选题进入结构化内容生产、修改、版本和素材交付流程。")
    section = st.radio(
        "功能区",
        SECTIONS,
        horizontal=True,
        key="content.section",
        label_visibility="collapsed",
    )
    st.divider()
    renderers = {
        "内容工作台": _workspace,
        "文章生成文案": _article_script,
        "主题直写": _topic_writer,
        "交易认知": _trading,
        "内容版本": _versions,
        "分镜与素材": _storyboard,
        "内容模板": _templates,
    }
    renderers[section]()
