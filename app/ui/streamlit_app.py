"""智行科技内部员工助手的现代 SaaS 工作台。"""
import httpx
import streamlit as st
from theme import theme_css

st.set_page_config(page_title="智行科技内部员工助手", page_icon="💬", layout="wide")
theme = st.segmented_control("主题", ["亮色", "暗色"], default="亮色", label_visibility="collapsed")
st.markdown(theme_css(theme or "亮色"), unsafe_allow_html=True)

st.markdown("<div class='hero'><h1>智行科技内部员工助手</h1><p class='muted'>差旅制度 · 办公 IT · 账号与权限</p><p class='status'>● 服务已连接后即可开始咨询</p></div>", unsafe_allow_html=True)

with st.sidebar:
    st.subheader("工作台设置")
    api_url = st.text_input("API 地址", "http://localhost:8000")
    st.subheader("快捷咨询")
    examples = ["差旅报销应在多久内提交？", "国内出差住宿每晚报销上限是多少？", "公司 VPN 无法连接时应该怎么处理？", "请帮我重置 VPN 密码"]
    for index, example in enumerate(examples):
        if st.button(example, key=f"example-{index}", width="stretch"):
            st.session_state["question"] = example
    st.info("密码重置、生产权限和数据导出等请求会自动转人工工单。")

st.markdown("<div class='saas-card'><h3>智能问答</h3><p class='muted'>请输入问题，系统仅根据知识库返回带来源的结果。</p></div>", unsafe_allow_html=True)
question = st.text_area("问题", key="question", placeholder="例如：差旅报销应在多久内提交？", height=110)

if st.button("开始咨询", type="primary") and question.strip():
    st.markdown("<div class='saas-card'><h3>回答</h3></div>", unsafe_allow_html=True)
    answer_placeholder = st.empty()
    metadata: dict[str, object] | None = None
    error_message: str | None = None

    with st.spinner("正在检索知识库并生成回答…"):
        try:
            resp = httpx.post(
                f"{api_url}/chat",
                json={"question": question},
                timeout=60,
            )
            resp.raise_for_status()
            metadata = resp.json()
        except (httpx.RequestError, ValueError) as exc:
            error_message = f"API 请求失败：{exc}"

    if error_message:
        st.error(error_message)
    elif metadata is None:
        st.error("未收到服务端最终结果，请稍后重试。")
    else:
        data = metadata
        answer = str(data.get("answer", ""))
        if answer:
            answer_placeholder.markdown(answer)
        if data["route"] == "ticket":
            st.warning(f"已转交支持工单\n\n工单编号：`{data['ticket_id']}`")
            answer = ""
            answer_placeholder.empty()
            answer_placeholder.write(data["answer"])
        if data["citations"]:
            st.markdown("<div class='saas-card'><h3>知识来源</h3></div>", unsafe_allow_html=True)
            for citation in data["citations"]:
                st.caption(f"📄 {citation['title']}：{citation['excerpt'][:140]}…")
        a, b, c = st.columns(3)
        a.metric("置信度", data["confidence"])
        b.metric("处理路径", data["route"])
        c.metric("耗时", f"{data['latency_ms']}ms")
        st.caption(f"追踪编号：`{data['trace_id']}`")
