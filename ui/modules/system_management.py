from __future__ import annotations

import os

import streamlit as st

from ui.components.layout import metric_row, page_header, structured_placeholder
from ui.core.access import is_system_admin


def _profile() -> None:
    left, right = st.columns(2)
    with left:
        st.text_input("账号定位", placeholder="例如：面向普通用户的 Web3 热点解读", disabled=True)
        st.text_area("目标受众", placeholder="年龄、认知水平、兴趣和主要问题", disabled=True)
        st.multiselect("重点领域", ["Web3", "AI", "科技", "网络安全", "宏观"], disabled=True)
        st.selectbox("常用时长", ["30秒", "1分钟", "3分钟", "5分钟"], disabled=True)
    with right:
        st.text_area("内容风格", placeholder="表达方式、语气、节奏和结构偏好", disabled=True)
        st.text_area("禁用表达", placeholder="不允许出现的承诺、表述和敏感词", disabled=True)
        st.text_area("历史爆款与失败案例", placeholder="用于后续内容生成和复盘", disabled=True)
        st.button("保存账号画像", type="primary", disabled=True, use_container_width=True)


def _users() -> None:
    user = st.session_state.get("auth_user") or {}
    metric_row([("当前用户", user.get("username", "-"), None), ("当前角色", "普通用户", None), ("有效会话", 1, None), ("待处理邀请", 0, None)])
    st.dataframe(
        [{"用户名": user.get("username", "-"), "显示名称": user.get("display_name") or "-", "邮箱": user.get("email", "-"), "角色": "普通用户", "状态": "启用"}],
        hide_index=True,
        use_container_width=True,
    )
    structured_placeholder("角色与权限", "预留管理员、编辑/研究、审核和运营角色，以及模块级权限。", fields=["角色", "模块权限", "数据范围", "配置可见性"], actions=["新增用户", "分配角色", "停用账号"])


def _sources() -> None:
    metric_row([("RSS 源", 28, None), ("事件源", 6, None), ("Web3 热点源", 16, None), ("启用热点源", 15, None)])
    st.dataframe(
        [
            {"数据源组": "RSS 消息", "配置文件": "config/rss_sources.json", "数量": 28, "状态": "已使用"},
            {"数据源组": "事前事件", "配置文件": "config/event_sources.json", "数量": 6, "状态": "已使用"},
            {"数据源组": "Web3 热点", "配置文件": "config/web3_hot_sources.json", "数量": 16, "状态": "已使用"},
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.caption("当前只展示配置摘要，避免普通页面直接改写生产配置文件。")
    st.button("新增数据源", disabled=True)


def _prompts() -> None:
    st.dataframe(
        [
            {"Prompt": "默认视频内容包", "场景": "文章/主题", "版本": "代码内置", "状态": "已使用"},
            {"Prompt": "事前选题", "场景": "未来事件", "版本": "代码内置", "状态": "已使用"},
            {"Prompt": "Web3 热点内容", "场景": "热点消息", "版本": "代码内置", "状态": "已使用"},
            {"Prompt": "交易认知", "场景": "知识检索", "版本": "代码内置", "状态": "已使用"},
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.warning("Prompt 属于内部生产资产。后续只有管理员可查看正文和版本历史。")
    st.button("新建 Prompt 版本", disabled=True)


def _models() -> None:
    configured = bool(os.getenv("OPENAI_API_KEY"))
    metric_row([("默认模型", os.getenv("OPENAI_MODEL", "未配置"), None), ("接口状态", "已配置" if configured else "未配置", None), ("今日调用", "--", None), ("今日成本", "--", None)])
    structured_placeholder("模型路由", "管理文本生成模型、基础地址、超时、降级模型和场景绑定，不显示完整密钥。", fields=["供应商", "模型", "适用场景", "超时", "降级策略", "状态"], actions=["测试模型", "设置默认", "查看调用记录"])


def _api_config() -> None:
    rows = [
        {"配置": "LLM API", "状态": "已配置" if os.getenv("OPENAI_API_KEY") else "未配置", "敏感": "是"},
        {"配置": "X API", "状态": "已配置" if os.getenv("X_BEARER_TOKEN") else "未配置", "敏感": "是"},
        {"配置": "LunarCrush", "状态": "已配置" if os.getenv("LUNARCRUSH_API_KEY") else "未配置", "敏感": "是"},
        {"配置": "FastAPI 地址", "状态": "远程模式" if os.getenv("API_BASE_URL") else "Streamlit 直连模式", "敏感": "否"},
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.info("密钥值不会在页面中显示。Streamlit Cloud 继续通过 Secrets 管理，本地继续兼容 `.env`。")
    st.button("更新 API 配置", disabled=True)


def _rules() -> None:
    st.dataframe(
        [
            {"规则组": "RSS 热点评分", "用途": "消息筛选", "状态": "代码内置", "最后更新": "-"},
            {"规则组": "Web3 热点评分", "用途": "热点排行", "状态": "配置 + 代码", "最后更新": "-"},
            {"规则组": "事件关键词", "用途": "事件分类", "状态": "配置文件", "最后更新": "-"},
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.warning("评分权重属于内部选题标准，后续仅管理员可编辑。")


def _tasks() -> None:
    metric_row([("运行中", 0, None), ("等待中", 0, None), ("今日完成", 0, None), ("今日失败", 0, None)])
    st.dataframe([{"任务": "暂无后台任务", "当前阶段": "-", "完成数量": 0, "总数量": 0, "完成比例": "0%", "新增": 0, "去重": 0, "失败": 0, "可重试": "否"}], hide_index=True, use_container_width=True)


def _logs() -> None:
    columns = st.columns([2, 1, 1, 1])
    columns[0].text_input("搜索日志", placeholder="用户、操作或对象", key="system.logs.search")
    columns[1].selectbox("模块", ["全部", "认证", "信息", "选题", "内容", "发布", "配置"], key="system.logs.module")
    columns[2].selectbox("结果", ["全部", "成功", "失败"], key="system.logs.result")
    columns[3].selectbox("时间", ["今天", "最近 7 天", "最近 30 天"], key="system.logs.period")
    st.dataframe([{"时间": "-", "用户": "-", "模块": "-", "操作": "暂无审计日志", "对象": "-", "结果": "-"}], hide_index=True, use_container_width=True)


def _security() -> None:
    left, right = st.columns(2)
    with left:
        structured_placeholder("登录与会话", "管理会话有效期、登录失败限制、设备和强制退出。", fields=["会话有效期", "失败锁定", "当前设备", "活跃会话"], actions=["撤销其他会话", "保存策略"])
    with right:
        structured_placeholder("敏感配置保护", "控制 Prompt、评分规则、API Token、数据库配置和原始账号数据的访问。", fields=["配置加密", "显示脱敏", "权限审计", "导出限制"], actions=["运行安全检查", "查看风险"])


def render_system_management() -> None:
    if not is_system_admin(st.session_state.get("auth_user")):
        st.error("无权访问系统管理。该页面仅对系统管理员开放。")
        st.stop()

    page_header("系统管理", "集中管理账号画像、用户权限、数据源、模型、内部规则、任务和安全配置。", stage="管理员框架")
    tabs = st.tabs(["账号画像", "用户与权限", "数据源管理", "Prompt 管理", "模型配置", "API 配置", "评分规则", "任务管理", "操作日志", "安全设置"])
    renderers = [_profile, _users, _sources, _prompts, _models, _api_config, _rules, _tasks, _logs, _security]
    for tab, renderer in zip(tabs, renderers):
        with tab:
            renderer()
