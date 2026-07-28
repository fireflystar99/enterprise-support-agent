"""Streamlit demo UI for Enterprise Support Agent."""
import httpx
import streamlit as st

API_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

st.set_page_config(page_title="Enterprise Support Agent", page_icon="🏢")
st.title("Enterprise Support Agent")

st.markdown("Ask a policy or IT support question. Answers are cited from the knowledge base.")

with st.expander("Example questions"):
    st.markdown("- How do I submit a travel expense?")
    st.markdown("- What is the limit for hotel reimbursement?")
    st.markdown("- Are mini-bar charges reimbursable?")
    st.markdown("- How do I connect to VPN?")
    st.markdown("- Please reset my VPN password (triggers ticket)")

question = st.text_input("Your question", placeholder="e.g., How do I submit a travel expense?")

if st.button("Ask") and question:
    with st.spinner("Consulting knowledge base..."):
        try:
            response = httpx.post(
                f"{API_URL}/chat",
                json={"question": question},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Answer")
                if data["route"] == "ticket":
                    st.warning("📋 Routed to support ticket")
                    st.info(f"Ticket ID: `{data['ticket_id']}`")
                st.write(data["answer"])

                if data["citations"]:
                    st.subheader("Sources")
                    for c in data["citations"]:
                        st.caption(f"📄 {c['title']}: {c['excerpt'][:100]}...")

            with col2:
                st.subheader("Metadata")
                st.metric("Confidence", data["confidence"])
                st.metric("Route", data["route"])
                st.metric("Latency", f"{data['latency_ms']}ms")
                st.caption(f"Trace ID: `{data['trace_id']}`")

        except httpx.RequestError as e:
            st.error(f"API request failed: {e}")
