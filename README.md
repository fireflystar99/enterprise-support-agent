# Enterprise Support Agent — 企业支持代理

基于 Python 的企业内部支持问答系统。仅凭授权的知识库证据回答，标注来源，在证据不足或操作敏感时创建模拟工单。

## 快速启动

```bash
docker compose up
```

打开 http://localhost:8501 使用演示界面，或 http://localhost:8000/docs 查看 API 文档。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | — | DeepSeek API 密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | LLM 提供商地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `DATABASE_URL` | `postgresql+psycopg://app:app@localhost:5432/support_agent` | PostgreSQL 连接字符串 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding 模型名称 |
| `ADMIN_TOKEN` | — | 管理接口（`/traces`、`/tickets`）的访问令牌 |
| `USER_ID` | `demo` | 默认用户标识（用于访问控制） |

## 本地启动（不含 Docker）

```bash
# 安装依赖
uv sync

# 启动 PostgreSQL（需包含 pgvector 扩展），然后执行：
uv run alembic upgrade head
uv run python scripts/seed_demo.py
uv run uvicorn app.api.main:app --reload
```

## 演示命令

```bash
# 知识库内的问题
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "How do I submit a travel expense?"}'

# 敏感请求（自动转为工单）
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"question": "Please reset my VPN password"}'

# 查看查询轨迹（需要管理员令牌）
curl http://localhost:8000/traces/{trace_id} -H "X-Admin-Token: $ADMIN_TOKEN"
```

## 测试

```bash
# 快速单元测试（不需要数据库或 LLM）
pytest -m "not integration" -v

# 集成测试（需要 PostgreSQL + pgvector）
pytest -m integration -v

# 全部测试
pytest -v
```

## 评估实验

```bash
# 运行开发集评估
python scripts/run_evaluation.py --version v1 --split development

# 运行保留集评估（最终报告用）
python scripts/run_evaluation.py --version v3 --split holdout
```

结果保存在 `artifacts/<版本号>/<时间戳>/` 目录中，包含逐条结果和聚合指标。

## 架构

```
客户端 → FastAPI → 支持代理 → search_knowledge_base / create_ticket
                                   ↓
                          PostgreSQL + pgvector
```

## 实验配置对比

| 版本 | 检索方式 | 引用校验 | 访问过滤 |
|------|---------|---------|---------|
| V1 | 纯向量检索 | 关闭 | 关闭 |
| V2 | BM25 + 向量混合 | 关闭 | 关闭 |
| V3 | 混合检索 | 强制引用 | 开启 |
| production | 混合检索 | 强制引用 | 开启 |

执行 `python scripts/run_evaluation.py --version <版本号> --split development` 获取实际指标。

## 已知限制

- 工单通过 ORM 存储在 PostgreSQL 中，附带内存缓存
- 访问控制使用模拟的部门→权限级别映射，未接入 SSO/OIDC
- 不执行任何特权操作（密码重置、权限变更等）—— 此类请求全部转为工单
- embedding 模型首次运行时需要下载
- 管理接口（`/traces`、`/tickets`）通过可配置的共享令牌（`ADMIN_TOKEN`）保护
