"""智行科技支持工单管理工作台。"""

from collections import Counter

import httpx
import streamlit as st
from theme import theme_css
from ticket_api import fetch_tickets, update_ticket_status

STATUS_LABELS = {
    "all": "全部状态",
    "open": "待处理",
    "in_progress": "处理中",
    "resolved": "已解决",
}
RISK_LABELS = {"all": "全部风险", "low": "低风险", "medium": "中风险", "high": "高风险"}


def _format_created_at(value: str | None) -> str:
    if not value:
        return "—"
    return value.replace("T", " ").replace("+00:00", " UTC")


def _ticket_option_label(ticket_id: str, tickets: list[dict]) -> str:
    ticket = next(item for item in tickets if item["id"] == ticket_id)
    return f"{ticket_id[:8]} · {ticket['question'][:24]}"


st.set_page_config(
    page_title="工单管理中心 | 智行科技",
    page_icon=":material/support_agent:",
    layout="wide",
)

st.session_state.setdefault("ticket_theme", "亮色")
st.session_state.setdefault("selected_ticket_id", None)

header_left, header_right = st.columns([5, 1], vertical_alignment="center")
with header_left:
    st.title(":material/support_agent: 支持工单中心")
    st.caption("智行科技内部员工助手 · 管理需要人工处理的敏感请求")
with header_right:
    theme = st.segmented_control(
        "页面主题",
        ["亮色", "暗色"],
        key="ticket_theme",
        label_visibility="collapsed",
    )
st.markdown(theme_css(theme or "亮色"), unsafe_allow_html=True)

with st.sidebar:
    st.header("连接与筛选")
    api_url = st.text_input("API 地址", value="http://localhost:8000")
    admin_token = st.text_input("管理员令牌", type="password")
    st.caption("令牌仅用于本次浏览器会话中的 API 请求，不会显示在页面中。")
    st.divider()
    status_filter = st.selectbox("工单状态", list(STATUS_LABELS), format_func=STATUS_LABELS.get)
    risk_filter = st.selectbox("风险等级", list(RISK_LABELS), format_func=RISK_LABELS.get)
    refresh = st.button("刷新工单", icon=":material/refresh:", type="primary", width="stretch")

if not admin_token:
    st.info("请输入管理员令牌以加载工单。令牌需与 API 服务的 `ADMIN_TOKEN` 一致。")
    st.stop()

request_status = None if status_filter == "all" else status_filter
request_risk = None if risk_filter == "all" else risk_filter

try:
    with st.spinner("正在加载工单…"):
        tickets = fetch_tickets(api_url, admin_token, request_status, request_risk)
except httpx.HTTPStatusError as exc:
    st.error(f"无法加载工单：API 返回 {exc.response.status_code}。请检查管理员令牌和服务状态。")
    st.stop()
except httpx.RequestError as exc:
    st.error(f"无法连接 API：{exc}。请确认 http://localhost:8000 正在运行。")
    st.stop()

if refresh:
    st.rerun()

counts = Counter(ticket["status"] for ticket in tickets)
metrics = st.columns(4)
metrics[0].metric("待处理", counts["open"], border=True)
metrics[1].metric("处理中", counts["in_progress"], border=True)
metrics[2].metric("已解决", counts["resolved"], border=True)
metrics[3].metric("当前筛选结果", len(tickets), border=True)

st.space("small")
list_column, detail_column = st.columns([3, 2], gap="large")

with list_column, st.container(border=True):
    st.subheader("工单列表")
    if not tickets:
        st.caption("当前筛选条件下没有工单。")
    else:
        ticket_ids = [ticket["id"] for ticket in tickets]
        if st.session_state.selected_ticket_id not in ticket_ids:
            st.session_state.selected_ticket_id = ticket_ids[0]
        table_rows = [
            {
                "工单编号": ticket["id"],
                "状态": STATUS_LABELS.get(ticket["status"], ticket["status"]),
                "风险": RISK_LABELS.get(ticket["risk_level"], ticket["risk_level"]),
                "创建时间": _format_created_at(ticket.get("created_at")),
                "问题": ticket["question"],
            }
            for ticket in tickets
        ]
        st.dataframe(table_rows, hide_index=True, width="stretch", height=440)
        st.selectbox(
            "选择要查看的工单",
            ticket_ids,
            format_func=lambda ticket_id: _ticket_option_label(ticket_id, tickets),
            key="selected_ticket_id",
        )

with detail_column, st.container(border=True):
    st.subheader("工单详情")
    selected_ticket = next(
        (ticket for ticket in tickets if ticket["id"] == st.session_state.selected_ticket_id),
        None,
    )
    if selected_ticket is None:
        st.caption("从左侧列表选择一张工单。")
    else:
        st.markdown(f"**{selected_ticket['question']}**")
        st.caption(f"工单编号：`{selected_ticket['id']}`")
        st.write("转交原因")
        st.info(selected_ticket["reason"] or "未提供")
        risk = selected_ticket["risk_level"]
        st.markdown(
            f"风险等级：<span class='risk-{risk}'>{RISK_LABELS.get(risk, risk)}</span>",
            unsafe_allow_html=True,
        )
        st.caption(f"创建时间：{_format_created_at(selected_ticket.get('created_at'))}")
        st.divider()
        with st.form("ticket-status-form"):
            new_status = st.selectbox(
                "更新状态",
                ["open", "in_progress", "resolved"],
                index=["open", "in_progress", "resolved"].index(selected_ticket["status"]),
                format_func=STATUS_LABELS.get,
            )
            submitted = st.form_submit_button("保存状态", type="primary", width="stretch")
        if submitted:
            try:
                update_ticket_status(api_url, admin_token, selected_ticket["id"], new_status)
                st.success("工单状态已保存。")
                st.rerun()
            except httpx.HTTPStatusError as exc:
                st.error(f"保存失败：API 返回 {exc.response.status_code}。")
            except httpx.RequestError as exc:
                st.error(f"保存失败：无法连接 API（{exc}）。")
