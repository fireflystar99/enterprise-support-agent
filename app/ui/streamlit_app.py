"""智行科技内部员工助手的 Streamlit 演示页面。"""
import httpx
import streamlit as st

st.set_page_config(page_title="智行科技内部员工助手", page_icon="💬")

API_URL = st.sidebar.text_input("API 地址", value="http://localhost:8000")
st.title("智行科技内部员工助手")
st.markdown("可咨询差旅制度、办公 IT 与账号权限问题；回答仅基于知识库并附带来源。")

with st.expander("示例问题"):
    st.markdown("- 差旅报销应在多久内提交？")
    st.markdown("- 国内出差住宿每晚报销上限是多少？")
    st.markdown("- 公司 VPN 无法连接时应该怎么处理？")
    st.markdown("- 请帮我重置 VPN 密码（将创建工单）")

question = st.text_input("请输入你的问题", placeholder="例如：差旅报销应在多久内提交？")

if st.button("开始咨询") and question:
    with st.spinner("正在查询知识库…"):
        try:
            response = httpx.post(f"{API_URL}/chat", json={"question": question}, timeout=30)
            response.raise_for_status()
            data = response.json()
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("回答")
                if data["route"] == "ticket":
                    st.warning("📋 已转交支持工单")
                    st.info(f"工单编号：`{data['ticket_id']}`")
                st.write(data["answer"])
                if data["citations"]:
                    st.subheader("来源")
                    for citation in data["citations"]:
                        st.caption(f"📄 {citation['title']}：{citation['excerpt'][:100]}…")
            with col2:
                st.subheader("请求信息")
                st.metric("置信度", data["confidence"])
                st.metric("处理路径", data["route"])
                st.metric("耗时", f"{data['latency_ms']}ms")
                st.caption(f"追踪编号：`{data['trace_id']}`")
        except httpx.RequestError as exc:
            st.error(f"API 请求失败：{exc}")
