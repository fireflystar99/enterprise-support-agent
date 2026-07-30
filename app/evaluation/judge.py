"""LLM 评估器——可选的答案忠实度评分。需要 API key。"""
from app.core.config import settings


def judge_answer_faithfulness(expected: str, actual: str) -> int | None:
    """评估预期答案与实际答案的语义等价程度（1-5 分）。
    LLM 未配置时返回 None。"""
    if not settings.llm_api_key or not expected.strip() or not actual.strip():
        return None

    try:
        from openai import OpenAI
        client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

        response = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            messages=[{
                "role": "user",
                "content": (
                    f"Expected answer: {expected}\n"
                    f"Actual answer: {actual}\n\n"
                    "Rate the semantic equivalence on a scale of 1-5 "
                    "(5 = identical meaning, 1 = completely different). "
                    "Reply with a single digit (1-5) and nothing else."
                ),
            }],
        )
        raw = response.choices[0].message.content.strip()
        score = int(raw[0]) if raw and raw[0].isdigit() else None
        return score if score is not None and 1 <= score <= 5 else None
    except (OSError, ValueError, Exception):  # noqa: BLE001
        return None
