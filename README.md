# 智行科技内部员工助手

面向中文互联网科技公司的内部支持演示系统。系统使用 BGE-M3 与 PostgreSQL pgvector 检索差旅、办公 IT 和账号权限知识；普通问题返回带来源的答案，敏感操作自动创建工单，不执行密码重置或权限变更。

## 启动顺序

### 检索模型下载与降级

首次启动 API 时会下载 BGE-M3 向量模型和 BGE Cross-Encoder 重排序模型。请在启动前设置 Hugging Face 端点（PowerShell）：

```powershell
$env:HF_ENDPOINT = "https://huggingface.co"
```

模型下载完成后，服务会复用本地缓存。若重排序模型不可用（例如网络不可达或模型文件缺失），检索不会阻止服务启动，而会安全降级为仅使用 RRF 融合排序的结果。

首次启动或重新写入演示知识库时，在项目目录依次运行：

```powershell
docker compose up -d db
uv run alembic upgrade head
uv run python scripts/seed_demo.py --clear
uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

另开一个 PowerShell 窗口：

```powershell
uv run streamlit run app/ui/streamlit_app.py --server.port 8501
```

浏览器打开 `http://localhost:8501`。数据库 Docker 卷未删除时，后续重启只需启动数据库、API 和 Streamlit。

### 管理工单

另开一个 PowerShell 窗口运行：

```powershell
uv run streamlit run app/ui/ticket_management.py --server.port 8502
```

浏览器打开 `http://localhost:8502`，输入 API 地址和与 API 服务 `ADMIN_TOKEN` 一致的管理员令牌。管理页可以按状态、风险等级筛选工单，并将工单更新为“处理中”或“已解决”。

## 中文演示问题

- `差旅报销应在多久内提交？`
- `国内出差住宿每晚报销上限是多少？`
- `请帮我重置 VPN 密码`
- `帮我开通生产环境管理员权限`

## 质量门禁

```powershell
uv run ruff check .
uv run pytest -m "not integration" -v
```

## 已知限制

- 当前普通回答路径为检索文本拼接并附来源，不是 LLM 生成回答。
- 权限映射为演示实现，真实企业应接入 SSO/OIDC。
- 演示制度和数据均为虚构内容。
