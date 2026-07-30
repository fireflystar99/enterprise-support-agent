"""基于检索证据调用 DeepSeek 的受限流式客户端。"""
from collections.abc import Iterator, Sequence

from openai import OpenAI

from app.core.config import settings

SYSTEM_PROMPT = """你是企业内部知识助手。仅根据用户消息中的“知识库证据”回答。
使用简洁中文；不得编造制度、金额、审批规则或来源。证据不足时请明确说明无法确认。
不得执行、指导或绕过密码重置、权限提升、数据导出等敏感操作。"""

_client: OpenAI | None = None


class DeepSeekError(RuntimeError):
    """DeepSeek 不可用时对业务层暴露的受控异常。"""


def _get_client() -> OpenAI:
    """按进程复用 API 客户端，避免每个请求重复创建 HTTP 连接池。"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
    return _client


def _build_user_prompt(question: str, evidence: Sequence[str]) -> str:
    evidence_text = "\n\n".join(
        f"[{index}] {content}" for index, content in enumerate(evidence, start=1)
    )
    return f"用户问题：{question}\n\n知识库证据：\n{evidence_text}"


def stream_answer(question: str, evidence: Sequence[str]) -> Iterator[str]:
    """逐段返回 DeepSeek 基于证据生成的回答文本。"""
    if not settings.llm_api_key:
        raise DeepSeekError("DeepSeek API key is not configured")

    try:
        completion = _get_client().chat.completions.create(
            model=settings.llm_model,
            stream=True,
            timeout=settings.llm_timeout_seconds,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(question, evidence)},
            ],
        )
        for chunk in completion:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except DeepSeekError:
        raise
    except Exception as exc:
        raise DeepSeekError("DeepSeek generation failed") from exc


def generate_answer(question: str, evidence: Sequence[str]) -> str:
    """收集流式 token，供兼容的非流式接口复用。"""
    return "".join(stream_answer(question, evidence)).strip()
