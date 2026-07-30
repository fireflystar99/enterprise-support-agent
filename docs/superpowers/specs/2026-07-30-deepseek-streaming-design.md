# DeepSeek API 流式回答设计

## 目标

在保留现有中文企业知识库检索、安全路由、权限过滤、Grounding、工单和 Trace 的前提下，接入 DeepSeek 云端 API，为可安全回答的问题提供逐字流式中文回答。

## 范围

- 使用 OpenAI 兼容 SDK 调用 `https://api.deepseek.com`。
- 默认模型改为 `deepseek-v4-flash`。
- 新增 FastAPI SSE 流式接口。
- Streamlit 使用真实流式响应显示生成文本。
- DeepSeek 仅基于检索出的知识块回答，不获得数据库连接、工单操作权限或浏览器可见的 API Key。

## 不在范围内

- 不替换 BGE-M3 embedding、BM25、RRF 或 Reranker。
- 不在前端直接调用 DeepSeek。
- 不实现多轮聊天记忆、函数调用或自动执行外部操作。

## 请求流程

```text
用户问题
→ SupportAgent 检索、权限过滤和敏感路由
→ 敏感/无证据：创建工单，不调用 LLM
→ 正常回答：问题 + 检索 Chunk 作为受限证据上下文
→ DeepSeek stream=True
→ FastAPI SSE token 事件
→ Streamlit 逐字显示
→ metadata 事件携带引用、Trace ID、耗时
```

## 模块边界

### `app/llm/deepseek.py`

- 延迟创建 OpenAI 客户端，读取 `settings.llm_api_key`、`settings.llm_base_url` 与 `settings.llm_model`。
- 负责构造系统提示词和证据上下文。
- 暴露同步迭代器，逐个产出文本 token。
- API Key 缺失、超时或上游调用异常时抛出受控的 `DeepSeekError`，不回显密钥或上游响应细节。

### `SupportAgent`

- 继续先完成检索、安全路由、权限过滤和 Grounding 前置判断。
- 仅当路由为 `answer` 且存在证据时调用 DeepSeek。
- 不再将检索文本直接作为最终自然语言回答；检索块仍作为 citations 返回。
- DeepSeek 调用失败时创建低风险支持工单，并持久化失败路径的 Trace。

### FastAPI

- 保留现有 `POST /chat` 作为兼容的非流式接口。
- 新增 `POST /chat/stream`，使用 `text/event-stream` 返回：
  - `token`：增量回答文本；
  - `metadata`：最终引用、route、confidence、ticket_id、trace_id、latency_ms；
  - `error`：受控错误信息。
- API 层不保存或返回 `LLM_API_KEY`。

### Streamlit

- 员工问答页改为调用 `/chat/stream`。
- token 通过占位区域逐步渲染。
- 收到 metadata 后显示引用、路由、耗时和 Trace ID。
- 连接异常显示中文错误提示，不显示 Python 堆栈或密钥。

## 提示词与安全约束

系统提示词必须要求模型：

1. 仅根据给定企业知识证据回答；
2. 证据不足时明确说明无法确认；
3. 不执行或指导密码重置、权限提升、数据导出等敏感操作；
4. 使用简洁中文回答；
5. 不编造制度、金额、审批规则或来源；
6. 每个可验证结论后使用对应证据编号，例如 `[1]` 或 `[2]`。

安全路由仍在 LLM 调用之前执行，因此模型不会处理被拦截的敏感请求。

## 配置

`.env`：

```dotenv
LLM_API_KEY=your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

`.env.example` 只保留占位符，真实 `.env` 必须继续被 Git 忽略。

## 错误处理

- API Key 缺失：应用返回受控错误，不调用上游。
- 上游超时、网络异常、限流或返回无文本：创建工单，响应不伪造答案。
- 流已经发送 token 后发生异常：发送 `error` 事件并结束流；客户端保留已显示文本并提示用户重试。

## 验收与测试

- 单元测试：DeepSeek 客户端使用正确 base URL、模型和证据上下文；流 token 可迭代。
- Agent 测试：正常问题调用 LLM；敏感问题和无证据问题绝不调用 LLM；LLM 异常转工单。
- API 测试：SSE 顺序输出 token 与 metadata；非流式 `/chat` 保持兼容。
- UI 测试：流式 metadata 可正确解析并显示引用。
- 回归：Ruff 通过，全部非集成测试通过。
