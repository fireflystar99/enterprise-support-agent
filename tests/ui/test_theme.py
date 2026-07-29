from app.ui.theme import theme_css


def test_theme_css_supports_light_and_dark() -> None:
    assert "#F6F8FC" in theme_css("亮色")
    assert "#0F172A" in theme_css("暗色")
