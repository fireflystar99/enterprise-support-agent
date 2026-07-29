"""Theme helpers for the Streamlit support workspace."""


def theme_css(theme: str) -> str:
    if theme == "暗色":
        background, surface, text, muted, primary = "#0F172A", "#172033", "#E5E7EB", "#94A3B8", "#38BDF8"
    else:
        background, surface, text, muted, primary = "#F6F8FC", "#FFFFFF", "#172033", "#64748B", "#2563EB"
    return f"""
    <style>
    .stApp {{ background: {background}; color: {text}; }}
    .saas-card {{ background: {surface}; color: {text}; border-radius: 16px; padding: 20px; margin: 10px 0; border: 1px solid {muted}33; }}
    .hero {{ padding: 18px 0 8px; }} .muted {{ color: {muted}; }}
    .status {{ color: {primary}; font-weight: 700; }}
    </style>
    """
