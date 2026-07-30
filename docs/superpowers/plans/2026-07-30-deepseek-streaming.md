# DeepSeek 流式回答 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让安全通过且有知识库证据的企业问答使用 DeepSeek V4-Flash 生成真实 SSE 流式中文回答，同时保持现有引用、工单和 Trace 行为。

**Architecture:** 新建独立的 `app.llm.deepseek` 模块封装 OpenAI 兼容 DeepSeek 调用与证据约束提示词。`SupportAgent` 先完成现有检索、安全路由、权限过滤和 Grounding，再将允许回答的证据交给 LLM；FastAPI 将 token 和最终 metadata 编码为 SSE，Streamlit 消费 SSE 并逐字展示。

**Tech Stack:** Python 3.12、FastAPI `StreamingResponse`、OpenAI Python SDK、DeepSeek API、Pydantic、httpx、Streamlit、pytest、Ruff。

---

## 文件结构

- Create: `app/llm/__init__.py` — LLM 模块包标记。
- Create: `app/llm/deepseek.py` — DeepSeek 客户端、证据提示词、同步 token 迭代器和受控异常。
- Create: `app/api/sse.py` — 无状态 SSE 编码函数，避免 API 路由混入协议细节。
- Modify: `app/core/config.py` — 默认模型改为 `deepseek-v4-flash`，新增生成超时配置。
- Modify: `.env.example` — 更新安全示例模型名。
- Modify: `app/support/agent.py` — 分离“准备检索结果”和“生成回答”，增加非流式与流式 LLM 路径。
- Modify: `app/api/main.py` — 增加 `/chat/stream`。
- Modify: `app/ui/streamlit_app.py` — 消费 SSE 并递增渲染 token。
- Modify: `tests/support/test_agent.py` — 覆盖安全路由与 LLM 调用边界。
- Modify: `tests/api/test_chat.py` — 覆盖 SSE 事件顺序和兼容的 `/chat`。
- Create: `tests/llm/test_deepseek.py` — 覆盖 DeepSeek 请求构造和异常封装。
- Create: `tests/api/test_sse.py` — 覆盖 SSE JSON 编码。
- Modify: `README.md` — 增加 DeepSeek API 配置与流式使用说明。

### Task 1: 受限 DeepSeek 客户端

**Files:**
- Create: `app/llm/__init__.py`
- Create: `app/llm/deepseek.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_deepseek.py`
- Modify: `app/core/config.py`
- Modify: `.env.example`

- [ ] **Step 1: 写出失败的 DeepSeek 客户端测试**

```python
from app.llm.deepseek import DeepSeekError, stream_answer


def test_stream_answer_uses_configured_client_and_evidence(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return [
                type("Chunk", (), {"choices": [type("Choice", (), {"delta": type("Delta", (), {"content": "答案"})()})()]})()
            ]

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("app.llm.deepseek._get_client", lambda: FakeClient())

    assert list(stream_answer("如何报销？", ["报销须在 30 天内提交。 "])) == ["答案"]
    assert captured["stream"] is True
    assert "30 天内提交" in captured["messages"][1]["content"]


def test_stream_answer_rejects_missing_api_key(monkeypatch):
    monkeypatch.setattr("app.llm.deepseek.settings.llm_api_key", "")
    with pytest.raises(DeepSeekError, match="not configured"):
        list(stream_answer("问题", ["证据"]))
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/llm/test_deepseek.py -q`

Expected: FAIL，提示 `app.llm.deepseek` 不存在。

- [ ] **Step 3: 实现最小 DeepSeek 客户端**

```python
class DeepSeekError(RuntimeError):
    """DeepSeek 调用不可用时的受控异常。"""


def stream_answer(question: str, evidence: list[str]) -> Iterator[str]:
    if not settings.llm_api_key:
        raise DeepSeekError("DeepSeek API key is not configured")
    completion = _get_client().chat.completions.create(
        model=settings.llm_model,
        stream=True,
        timeout=settings.llm_timeout_seconds,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(question, evidence)},
        ],
    )
    try:
        for chunk in completion:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as exc:  # noqa: BLE001
        raise DeepSeekError("DeepSeek generation failed") from exc
```

系统提示词必须要求“只根据证据回答、使用中文、不编造制度、不执行敏感动作，并在每个结论后添加对应的 `[编号]` 引用”；`_build_user_prompt()` 使用编号证据块并限制为调用方传入的文本。

- [ ] **Step 4: 更新配置默认值**

```python
llm_model: str = "deepseek-v4-flash"
llm_timeout_seconds: float = 30.0
```

将 `.env.example` 中的 `LLM_MODEL` 改为 `deepseek-v4-flash`，不写入真实密钥。

- [ ] **Step 5: 运行客户端测试与 Ruff**

Run: `uv run pytest tests/llm/test_deepseek.py -q && uv run ruff check app/llm app/core/config.py`

Expected: 测试通过，Ruff 零警告。

- [ ] **Step 6: 提交**

```bash
git add app/llm tests/llm app/core/config.py .env.example
git commit -m "feat: add constrained DeepSeek client"
```

### Task 2: Agent 的安全生成与工单兜底

**Files:**
- Modify: `app/support/agent.py`
- Modify: `tests/support/test_agent.py`

- [ ] **Step 1: 写出失败的 Agent 测试**

```python
def test_agent_uses_llm_only_after_safe_retrieval(monkeypatch):
    chunks = [RetrievedChunk(id="c1", content="报销须在 30 天内提交。", title="制度", section="时限", score=1.0)]
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = chunks
    monkeypatch.setattr("app.support.agent.generate_answer", lambda *_args: "请在 30 天内提交。")

    response = SupportAgent(retrieval_service=service).handle("如何报销？")

    assert response.answer == "请在 30 天内提交。"


def test_sensitive_question_never_calls_llm(monkeypatch):
    service = MagicMock(spec=RetrievalService)
    service.search.return_value = [RetrievedChunk(id="c1", content="VPN 密码由 IT 处理。", title="VPN", section="", score=1.0)]
    llm = MagicMock()
    monkeypatch.setattr("app.support.agent.generate_answer", llm)

    response = SupportAgent(retrieval_service=service).handle("请重置 VPN 密码")

    assert response.route == "ticket"
    llm.assert_not_called()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/support/test_agent.py -q`

Expected: 第一项因 `generate_answer` 不存在或未被调用而失败。

- [ ] **Step 3: 以最小改动实现非流式生成路径**

在 `app.llm.deepseek` 新增：

```python
def generate_answer(question: str, evidence: list[str]) -> str:
    return "".join(stream_answer(question, evidence)).strip()
```

在 `SupportAgent.handle()` 中，仅在现有 `Route.ANSWER`、citations 和 Grounding 均通过后调用：

```python
try:
    answer = generate_answer(question, [chunk.content for chunk in chunks])
except DeepSeekError:
    return self._ticket_response(
        question, trace_id, chunk_ids, start, "语言模型暂时不可用"
    )
```

将现有两处重复的工单构造提取为私有 `_ticket_response()`，确保 LLM 调用失败和敏感请求均写入 Trace。

- [ ] **Step 4: 运行 Agent 测试**

Run: `uv run pytest tests/support/test_agent.py tests/support/test_routing.py -q`

Expected: 敏感问题不调用 LLM；安全问题调用 LLM；LLM 异常返回工单。

- [ ] **Step 5: 提交**

```bash
git add app/llm/deepseek.py app/support/agent.py tests/support/test_agent.py
git commit -m "feat: generate grounded answers with DeepSeek"
```

### Task 3: SSE 事件协议与 `/chat/stream`

**Files:**
- Create: `app/api/sse.py`
- Modify: `app/api/main.py`
- Create: `tests/api/test_sse.py`
- Modify: `tests/api/test_chat.py`

- [ ] **Step 1: 写出失败的 SSE 编码与 API 测试**

```python
def test_encode_sse_emits_named_json_event():
    assert encode_sse("token", {"text": "你好"}) == 'event: token\\ndata: {"text":"你好"}\\n\\n'


def test_chat_stream_emits_tokens_then_metadata(client, monkeypatch):
    monkeypatch.setattr("app.api.main.support_agent.stream", lambda *_args, **_kwargs: iter([
        ("token", {"text": "报销"}),
        ("token", {"text": "须在 30 天内提交"}),
        ("metadata", {"route": "answer", "citations": [], "trace_id": "t1", "latency_ms": 1}),
    ]))

    response = client.post("/chat/stream", json={"question": "如何报销？"})

    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.index("event: token") < response.text.index("event: metadata")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/api/test_sse.py tests/api/test_chat.py -q`

Expected: FAIL，提示 `encode_sse` 或 `/chat/stream` 不存在。

- [ ] **Step 3: 实现 SSE 编码与 Agent 流接口**

`app/api/sse.py`：

```python
def encode_sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n"
```

`SupportAgent.stream()` 在安全判断后逐个 yield：

```python
yield "token", {"text": token}
yield "metadata", response.model_dump(mode="json")
```

当 LLM 在首个 token 前失败时，yield 单个 `metadata` 工单事件；当已有 token 后失败时，yield `error` 事件，内容固定为“回答生成中断，请稍后重试”。

`main.py`：

```python
@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    events = (encode_sse(event, payload) for event, payload in support_agent.stream(
        request.question, request.department, config=_production_config
    ))
    return StreamingResponse(events, media_type="text/event-stream")
```

- [ ] **Step 4: 运行 API 测试**

Run: `uv run pytest tests/api/test_sse.py tests/api/test_chat.py -q`

Expected: token、metadata 顺序正确；原有 `/chat` 测试仍通过。

- [ ] **Step 5: 提交**

```bash
git add app/api/sse.py app/api/main.py app/support/agent.py tests/api/test_sse.py tests/api/test_chat.py
git commit -m "feat: add DeepSeek chat streaming endpoint"
```

### Task 4: Streamlit 流式渲染、说明与回归

**Files:**
- Modify: `app/ui/streamlit_app.py`
- Modify: `README.md`
- Modify: `tests/ui/test_theme.py`

- [ ] **Step 1: 写出失败的 UI 协议测试**

```python
def test_stream_event_parser_keeps_utf8_token_and_metadata():
    events = list(parse_sse_lines([
        'event: token', 'data: {"text":"报销"}', '',
        'event: metadata', 'data: {"route":"answer","citations":[]}', '',
    ]))
    assert events == [("token", {"text": "报销"}), ("metadata", {"route": "answer", "citations": []})]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/ui/test_theme.py -q`

Expected: FAIL，提示 `parse_sse_lines` 不存在。

- [ ] **Step 3: 实现 Streamlit 流式消费**

在 `streamlit_app.py` 提取无副作用解析器：

```python
def parse_sse_lines(lines: Iterable[str]) -> Iterator[tuple[str, dict[str, object]]]:
    event = "message"
    for line in lines:
        if line.startswith("event: "):
            event = line.removeprefix("event: ")
        elif line.startswith("data: "):
            yield event, json.loads(line.removeprefix("data: "))
```

按钮点击后使用：

```python
with httpx.stream("POST", f"{api_url}/chat/stream", json={"question": question}, timeout=35) as response:
    response.raise_for_status()
    for event, payload in parse_sse_lines(response.iter_lines()):
        if event == "token":
            answer += str(payload["text"])
            answer_placeholder.markdown(answer)
        elif event == "metadata":
            metadata = payload
```

metadata 到达后复用既有引用、route、耗时与 Trace UI；`error` 事件显示中文提示。

- [ ] **Step 4: 更新 README**

在启动说明中增加：

```powershell
$env:LLM_API_KEY = "你的 DeepSeek API Key"
$env:LLM_MODEL = "deepseek-v4-flash"
```

明确说明真实密钥只能放在 `.env` 或环境变量，不能提交；Streamlit 通过本地 FastAPI 调用，浏览器不会接触 API Key。

- [ ] **Step 5: 执行全量回归**

Run: `uv run ruff check . && uv run pytest -m "not integration" -q`

Expected: Ruff 零警告，全部非集成测试通过。

- [ ] **Step 6: 提交**

```bash
git add app/ui/streamlit_app.py tests/ui/test_theme.py README.md
git commit -m "feat: stream DeepSeek answers in Streamlit"
```
