from __future__ import annotations

from datetime import datetime, timedelta, timezone

import streamlit as st

from app.services.web3_hot_collectors.social import load_x_key_accounts
from ui.components.layout import empty_state, filter_bar, metric_row, page_header, section_title, structured_placeholder
from ui.core.api_client import api_request
from app.services.title_translation import is_effective_chinese


FEED_ROWS = [
    {"时间": "10:32", "来源": "RSS", "分类": "Web3", "标题": "机构级加密服务出现新的合规进展", "热度": 82, "状态": "待判断"},
    {"时间": "10:18", "来源": "X", "分类": "市场", "标题": "多个行业账号集中讨论同一市场事件", "热度": 77, "状态": "观察中"},
    {"时间": "09:56", "来源": "事件日历", "分类": "监管", "标题": "本周重点政策窗口进入倒计时", "热度": 71, "状态": "已归并"},
]


def _display_title(article: dict) -> str:
    if is_effective_chinese(article.get("title_zh")):
        return str(article["title_zh"])
    if is_effective_chinese(article.get("title")):
        return str(article["title"])
    return ""


def _feed_table() -> None:
    st.dataframe(FEED_ROWS, use_container_width=True, hide_index=True)
    actions = st.columns([1, 1, 1, 4])
    actions[0].button("批量归并", disabled=True, use_container_width=True)
    actions[1].button("加入事件", disabled=True, use_container_width=True)
    actions[2].button("标记噪音", disabled=True, use_container_width=True)


def _overview() -> None:
    metric_row([
        ("今日新增", 126, "+18"),
        ("高热信息", 14, "+3"),
        ("待归并", 38, None),
        ("采集异常", 2, "-1"),
    ])
    st.write("")
    filter_bar(
        key_prefix="info.overview",
        categories=["全部", "Web3", "AI", "科技", "监管", "安全"],
        sources=["全部来源", "RSS", "X", "事件日历", "手动录入"],
        statuses=["全部状态", "待判断", "观察中", "已归并", "噪音"],
    )
    controls = st.columns([1, 1, 1, 4])
    controls[0].button("刷新信息", type="primary", use_container_width=True, disabled=True)
    controls[1].button("导入信息", use_container_width=True, disabled=True)
    controls[2].button("采集设置", use_container_width=True, disabled=True)
    section_title("综合信息流", "统一承载 RSS、X、事件日历、新闻 API 和人工录入信息。当前展示框架模拟数据。")
    _feed_table()


def _rss() -> None:
    articles = [
        article
        for article in st.session_state.get("rss.articles", [])
        if is_effective_chinese(article.get("title_zh") or article.get("title"))
    ]
    fetch_result = st.session_state.get("rss.fetch_result") or {}
    source_count = len({item.get("source_name") for item in articles if item.get("source_name")})
    metric_row(
        [
            ("启用消息源", 28, None),
            ("当前消息", len(articles), None),
            ("当前来源", source_count, None),
            ("最近新增", fetch_result.get("created", 0), None),
        ]
    )

    category_values = ["全部", "crypto", "ai", "tech"]
    category_labels = {"全部": "全部", "crypto": "加密货币", "ai": "人工智能", "tech": "科技新闻"}
    filter_columns = st.columns([1.2, 1.8, 1.3, 1])
    category = filter_columns[0].selectbox(
        "分类",
        category_values,
        format_func=lambda value: category_labels[value],
        key="rss.filter.category",
    )
    keyword = filter_columns[1].text_input(
        "关键词",
        placeholder="例如：Bitcoin、AI、监管",
        key="rss.filter.keyword",
    )
    time_range = filter_columns[2].selectbox(
        "时间范围",
        ["最近 6 小时", "最近 12 小时", "最近 24 小时", "最近 3 天", "最近 7 天"],
        index=2,
        key="rss.filter.time",
    )
    limit = filter_columns[3].number_input(
        "显示数量",
        min_value=5,
        max_value=20,
        value=10,
        step=5,
        key="rss.filter.limit",
    )

    params = {
        "category": None if category == "全部" else category,
        "keyword": keyword.strip() or None,
        "time_range": time_range,
        "limit": int(limit),
    }
    actions = st.columns([1, 1, 4])
    if actions[0].button("抓取最新 RSS", type="primary", use_container_width=True, key="rss.fetch"):
        with st.spinner("正在抓取并翻译最新 RSS 标题..."):
            try:
                result = api_request("POST", "/api/news/fetch", timeout=240)
                st.session_state["rss.fetch_result"] = result
                st.session_state["rss.articles"] = api_request("GET", "/api/news/topics", params=params)["items"]
                st.success(
                    f"抓取 {result.get('fetched', 0)} 条，新增 {result.get('created', 0)} 条，"
                    f"重复 {result.get('duplicates', 0)} 条"
                )
                if result.get("errors"):
                    st.warning("\n".join(str(error) for error in result["errors"]))
                st.rerun()
            except Exception as exc:
                st.error(f"抓取失败：{exc}")

    if actions[1].button("筛选消息", use_container_width=True, key="rss.filter"):
        with st.spinner("正在读取并筛选消息..."):
            try:
                st.session_state["rss.articles"] = api_request("GET", "/api/news/topics", params=params)["items"]
                st.rerun()
            except Exception as exc:
                st.error(f"筛选失败：{exc}")

    if fetch_result:
        st.caption(
            f"最近一次抓取：共 {fetch_result.get('fetched', 0)} 条，新增 {fetch_result.get('created', 0)} 条，"
            f"重复 {fetch_result.get('duplicates', 0)} 条"
        )

    st.divider()
    if not articles:
        empty_state("暂无 RSS 消息", "点击“抓取最新 RSS”采集消息，或点击“筛选消息”读取数据库中的已有文章。")
        return

    st.subheader("RSS 消息列表")
    st.caption("按热点评分展示。选择文章后，可在内容生产模块继续生成视频内容。")
    analyses = st.session_state.get("rss.analyses", {})
    selected_article_id = st.session_state.get("rss.selected_article_id")
    if selected_article_id:
        selected_article = next(
            (item for item in articles if int(item["id"]) == int(selected_article_id)),
            None,
        )
        if selected_article:
            with st.container(border=True):
                selected_body, selected_action = st.columns([5, 1.3])
                selected_body.markdown(
                    f"**当前已选素材：{_display_title(selected_article)}**"
                )
                selected_body.caption("该文章会自动出现在“内容生产 → 文章生成文案”。")
                if selected_action.button(
                    "清除选择",
                    key="rss.clear_selection",
                    use_container_width=True,
                ):
                    st.session_state["rss.selected_article_id"] = None
                    st.session_state["selected_article_id"] = None
                    st.session_state["workbench.selected_message_id"] = None
                    st.rerun()

    for article in articles:
        article_id = int(article["id"])
        with st.container(border=True):
            body, score, controls = st.columns([5.2, 1, 1.35])
            with body:
                visible_title = _display_title(article)
                st.markdown(f"### {visible_title}")
                if (
                    is_effective_chinese(article.get("title_zh"))
                    and article.get("title")
                    and article["title_zh"] != article["title"]
                ):
                    st.caption(article["title"])
                st.caption(
                    f"{article.get('source_name', '-')} · {article.get('category', '-')} · "
                    f"{article.get('published_at') or '时间未知'} · {article.get('recommendation_level', '-')}"
                )
                if article.get("summary"):
                    st.write(article["summary"])
                if article.get("link"):
                    st.markdown(f"[查看原文]({article['link']})")
            with score:
                st.metric("热度", f"{float(article.get('score') or 0):.0f}/100")
            with controls:
                if st.button("选择文章", key=f"rss.select.{article_id}", use_container_width=True):
                    st.session_state["rss.selected_article_id"] = article_id
                    st.session_state["selected_article_id"] = article_id
                    st.session_state["articles"] = articles
                    st.session_state["workbench.selected_message_id"] = article_id
                    st.session_state["content.section"] = "文章生成文案"
                    st.session_state["content.article.result"] = ""
                    st.session_state["content.article.result_article_id"] = None
                    st.success("已选为内容生产素材。请进入左侧“内容生产”继续生成文案。")
                if st.button("选题分析", key=f"rss.analyze.{article_id}", use_container_width=True):
                    with st.spinner("正在分析选题..."):
                        try:
                            analyses[article_id] = api_request(
                                "POST",
                                "/api/news/analyze",
                                payload={"article_id": article_id, "use_llm": True},
                            )
                            st.session_state["rss.analyses"] = analyses
                        except Exception as exc:
                            st.error(f"分析失败：{exc}")
            if article_id in analyses:
                analysis = analyses[article_id]
                with st.expander("选题分析结果", expanded=True):
                    st.write(analysis.get("one_sentence_summary", ""))
                    st.markdown(f"**为什么重要：** {analysis.get('why_important', '-')}")
                    st.markdown(f"**建议角度：** {analysis.get('video_angle', '-')}")
                    st.markdown(f"**建议形式：** {analysis.get('suggested_format', '-')}")
                    if analysis.get("recommended_titles"):
                        st.markdown("**建议标题：** " + " / ".join(analysis["recommended_titles"]))


def _web3_hot() -> None:
    metric_row([("活跃热点", 0, None), ("红色预警", 0, None), ("多源确认", 0, None), ("最近更新", "--:--", None)])
    filter_bar(
        key_prefix="info.web3",
        categories=["全部", "BTC", "ETH", "交易所", "监管", "安全"],
        sources=["全部来源", "RSS", "X", "LunarCrush"],
        statuses=["全部趋势", "new", "rising", "stable", "falling"],
    )
    structured_placeholder(
        "Web3 实时热点列表",
        "原热度墙的按来源展示、热度评分、趋势、多源确认、详情和内容生成入口将在此接入。",
        fields=["热度等级", "趋势状态", "热度分", "命中关键词", "发布时间"],
        actions=["立即抓取", "查看详情", "进入内容生产"],
        status="已有能力待接入",
    )


def _pre_events() -> None:
    metric_row([("未来 7 天事件", 0, None), ("高重要度", 0, None), ("待确认", 0, None), ("已生成选题", 0, None)])
    columns = st.columns([1.2, 1.2, 1.2, 3])
    columns[0].selectbox("时间窗口", ["未来 7 天", "未来 14 天", "未来 30 天"], key="info.pre.days")
    columns[1].selectbox("事件类型", ["全部", "宏观", "监管", "解锁", "AI 科技", "安全"], key="info.pre.type")
    columns[2].selectbox("重要度", ["全部", "高", "中", "低"], key="info.pre.level")
    columns[3].button("采集未来事件", type="primary", disabled=True)
    structured_placeholder(
        "自动事前事件",
        "接入现有六类事件采集器，展示事件时间、倒计时、重要度、影响对象和来源。",
        fields=["事件时间", "倒计时", "重要度", "分类", "状态"],
        actions=["刷新事件", "进入事前选题", "暂不处理"],
        status="已有能力待接入",
    )


def _parse_x_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _refresh_x_key_accounts() -> dict:
    result = api_request(
        "POST",
        "/api/web3-hot/fetch-now",
        payload={"source_type": "x_key_accounts"},
        timeout=120,
    )
    st.session_state["info.x.accounts.fetch_result"] = result
    st.session_state["info.x.accounts.items"] = api_request(
        "GET",
        "/api/web3-hot/list",
        params={"source_type": "x_key_accounts", "hours": 168, "limit": 200},
        timeout=60,
    ).get("items", [])
    return result


def _x_key_accounts() -> None:
    accounts = load_x_key_accounts()
    enabled_accounts = [account for account in accounts if account.get("enabled", True)]

    if not st.session_state.get("info.x.accounts.auto_fetch_attempted", False):
        st.session_state["info.x.accounts.auto_fetch_attempted"] = True
        with st.spinner("正在自动抓取重点账号最新推文..."):
            try:
                _refresh_x_key_accounts()
            except Exception as exc:
                st.session_state["info.x.accounts.fetch_result"] = {"errors": [str(exc)]}

    items = list(st.session_state.get("info.x.accounts.items", []))
    fetch_result = st.session_state.get("info.x.accounts.fetch_result") or {}
    errors = list(fetch_result.get("errors") or [])
    latest_fetched = max(
        (item.get("fetched_at") for item in items if item.get("fetched_at")),
        default=None,
    )
    metric_row(
        [
            ("监控账号", len(enabled_accounts), None),
            (
                "最近抓取",
                _parse_x_time(latest_fetched).astimezone().strftime("%m-%d %H:%M") if latest_fetched else "--",
                None,
            ),
            ("最近新增", int(fetch_result.get("inserted_count") or 0), None),
            ("失败批次", len(errors), None),
        ]
    )

    hour_options = {"最近 6 小时": 6, "最近 24 小时": 24, "最近 3 天": 72, "最近 7 天": 168}
    regions = ["全部地区", *dict.fromkeys(str(account.get("region") or "未分类") for account in accounts)]
    controls = st.columns([1.25, 1.25, 2, 1.2])
    hours_label = controls[0].selectbox(
        "时间范围",
        list(hour_options),
        index=1,
        key="info.x.accounts.hours",
    )
    region = controls[1].selectbox("地区", regions, key="info.x.accounts.region")
    account_keyword = controls[2].text_input(
        "账号搜索",
        placeholder="输入用户名或备注",
        key="info.x.accounts.search",
    )
    refresh_clicked = controls[3].button(
        "抓取最新推文",
        type="primary",
        width="stretch",
        key="info.x.accounts.refresh",
    )

    if refresh_clicked:
        with st.spinner("正在抓取重点账号最新推文..."):
            try:
                result = _refresh_x_key_accounts()
                st.success(
                    f"抓取 {result.get('fetched_count', 0)} 条，新增 {result.get('inserted_count', 0)} 条，"
                    f"更新 {result.get('updated_count', 0)} 条"
                )
            except Exception as exc:
                st.error(f"抓取失败：{exc}")
        items = list(st.session_state.get("info.x.accounts.items", []))
        fetch_result = st.session_state.get("info.x.accounts.fetch_result") or {}
        errors = list(fetch_result.get("errors") or [])

    if errors:
        st.warning("\n".join(str(error) for error in errors))

    account_by_username = {
        str(account.get("username", "")).lower(): account
        for account in accounts
    }
    keyword_lower = account_keyword.strip().lower()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hour_options[hours_label])
    filtered_items = []
    for item in items:
        username = str(item.get("author") or "").strip()
        account = account_by_username.get(username.lower(), {})
        published_at = _parse_x_time(item.get("published_at"))
        if published_at and published_at < cutoff:
            continue
        if region != "全部地区" and account.get("region") != region:
            continue
        searchable = f"{username} {account.get('display_name', '')}".lower()
        if keyword_lower and keyword_lower not in searchable:
            continue
        filtered_items.append(item)

    grouped: dict[str, list[dict]] = {}
    for item in filtered_items:
        username = str(item.get("author") or "未知账号")
        grouped.setdefault(username, []).append(item)

    st.subheader(f"重点账号推文（{len(grouped)} 个账号，{len(filtered_items)} 条）")
    if not filtered_items:
        empty_state(
            "暂无重点账号推文",
            "系统已完成本次查询。可调整时间或地区筛选，也可以点击“抓取最新推文”重试。",
        )
    else:
        for username, account_items in sorted(grouped.items(), key=lambda pair: pair[0].lower()):
            account = account_by_username.get(username.lower(), {})
            display_name = str(account.get("display_name") or "").strip()
            region_name = str(account.get("region") or "未分类")
            label = f"@{username}"
            if display_name:
                label += f" · {display_name}"
            with st.expander(f"{label}（{region_name}，{len(account_items)} 条）", expanded=True):
                for item in sorted(
                    account_items,
                    key=lambda value: value.get("published_at") or "",
                    reverse=True,
                ):
                    st.markdown(str(item.get("content") or item.get("title") or ""))
                    metrics = item.get("raw_metrics") or {}
                    published = _parse_x_time(item.get("published_at"))
                    published_text = published.astimezone().strftime("%m-%d %H:%M") if published else "时间未知"
                    st.caption(
                        f"{published_text} · 热度 {float(item.get('heat_score') or 0):.1f} · "
                        f"点赞 {int(metrics.get('likes') or 0)} · 转发 {int(metrics.get('reposts') or 0)} · "
                        f"回复 {int(metrics.get('replies') or 0)} · 引用 {int(metrics.get('quotes') or 0)}"
                    )
                    if item.get("link"):
                        st.markdown(f"[查看 X 原文]({item['link']})")
                    st.divider()

    with st.expander("查看重点账号配置"):
        st.dataframe(
            [
                {
                    "账号": f"@{account.get('username', '')}",
                    "备注": account.get("display_name") or "-",
                    "地区": account.get("region") or "未分类",
                    "优先级": account.get("priority") or "P2",
                    "状态": "启用" if account.get("enabled", True) else "停用",
                    "说明": account.get("validation_error") or "",
                }
                for account in accounts
            ],
            hide_index=True,
            width="stretch",
        )


def _x_messages() -> None:
    mode = st.radio(
        "X 消息功能",
        ["链接或正文录入", "重点账号采集"],
        horizontal=True,
        key="info.x.mode",
        label_visibility="collapsed",
    )
    st.divider()
    if mode == "链接或正文录入":
        st.text_area("X 消息", height=150, placeholder="每行粘贴一条 X 链接或消息正文", key="info.x.input")
        columns = st.columns([1, 1, 4])
        columns[0].button("解析消息", disabled=True, use_container_width=True)
        columns[1].button("批量加入信息流", disabled=True, use_container_width=True)
        st.info("该入口只建立交互结构，当前不会发送请求或消耗 X API 额度。")
    else:
        _x_key_accounts()


def _ranking() -> None:
    columns = st.columns([1.2, 1.2, 1.2, 3])
    columns[0].selectbox("榜单", ["综合热度", "增速最快", "讨论最多", "风险预警"], key="info.rank.type")
    columns[1].selectbox("周期", ["1 小时", "6 小时", "24 小时", "7 天"], key="info.rank.period")
    columns[2].selectbox("领域", ["全部", "Web3", "AI", "科技"], key="info.rank.category")
    st.dataframe(
        [
            {"排名": 1, "热点": "待接入实时数据", "热度": "--", "趋势": "--", "来源数": "--"},
            {"排名": 2, "热点": "待接入趋势计算", "热度": "--", "趋势": "--", "来源数": "--"},
        ],
        hide_index=True,
        use_container_width=True,
    )


def _detail() -> None:
    empty_state("尚未选择信息", "从综合信息流、RSS 或 Web3 实时热点中选择一条信息后，在此查看正文、来源和关联事件。")
    structured_placeholder(
        "信息处理",
        "详情页预留清洗去重、事件归并、来源核验和操作记录。",
        fields=["原始正文", "清洗结果", "相似信息", "关联事件", "可信度", "操作记录"],
        actions=["加入事件", "发起 AI 初评", "标记噪音"],
    )


def _tasks() -> None:
    metric_row([("运行中", 0, None), ("今日完成", 0, None), ("今日失败", 0, None), ("可重试", 0, None)])
    st.dataframe(
        [{"任务": "暂无采集任务", "阶段": "-", "进度": "0/0", "新增": 0, "去重": 0, "失败": 0, "更新时间": datetime.now().strftime("%H:%M")}],
        hide_index=True,
        use_container_width=True,
    )
    structured_placeholder("任务控制", "未来展示抓取进度、失败原因、重试和取消操作。", actions=["新建任务", "重试失败", "查看日志"])


def render_information_hotspots() -> None:
    page_header("信息与热点", "统一接入外部信息，完成展示、筛选、热点发现和采集任务管理。")
    tabs = st.tabs(["综合信息流", "RSS 消息", "Web3 实时热点", "自动事前事件", "X 消息", "热点排行", "信息详情", "采集任务"])
    renderers = [_overview, _rss, _web3_hot, _pre_events, _x_messages, _ranking, _detail, _tasks]
    for tab, renderer in zip(tabs, renderers):
        with tab:
            renderer()
