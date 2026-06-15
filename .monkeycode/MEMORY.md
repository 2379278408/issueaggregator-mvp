# 用户指令记忆

本文件记录会影响后续协作方式的长期指令与项目级记忆约束。

## 条目

[统一输出与记忆策略]
- Date: 2026-06-11
- Context: 用户要求初始化三层记忆机制，并确保存储记忆过程中只能删减增加
- Instructions:
  - 所有回复使用简体中文。
  - 项目使用三层记忆结构：L0 原子记忆、L1 主题摘要、L2 全局画像。
  - 记忆落盘采用追加式事件流；新增通过 append 写入，删减通过 prune/tombstone 写入。
  - 已写入事件禁止原地修改；任何调整都通过新增事件表达。

[前端交付偏好]
- Date: 2026-06-11
- Context: 用户要求继续优化前端界面并以当前源码仓库作为测试基线
- Instructions:
  - 前端页面文案优先全量汉化。
  - 视觉优化需要重点提升卡片、阴影、层级、留白和整体质感。
  - 提交前优先基于当前项目源码仓库执行测试与验证。

[管理接口安全配置]
- Date: 2026-06-11
- Context: Agent 在执行前后端优化与后端安全收敛时发现
- Category: 环境配置
- Instructions:
  - 后端管理接口通过 `ADMIN_API_NAMESPACE` 收口到 `/api/admin/<namespace>`。
  - 前端通过 `VITE_ADMIN_API_NAMESPACE` 访问管理接口，该值需要与后端保持一致。
  - 生产环境默认关闭 FastAPI 文档页，只有设置 `ENABLE_API_DOCS=true` 时才暴露 `/docs`。

[动态端到端测试依赖]
- Date: 2026-06-12
- Context: Agent 在执行隔离 FastAPI 端到端流程检查时发现
- Category: 测试方法
- Instructions:
  - 使用 `fastapi.testclient.TestClient` 做动态端到端检查前，环境需要可导入 `httpx`。
  - 当前项目常规后端测试命令仍为 `cd backend && python3 -m unittest discover -s tests`。

[公开反馈风控回归与开发库分流]
- Date: 2026-06-13
- Context: Agent 在补公开反馈风控动态验证脚本和隔离 SQLite 开发态数据文件时发现
- Category: 测试方法
- Instructions:
  - 公开反馈风控动态回归命令为 `cd backend && python3 tests/e2e_public_feedback_guardrails.py`。
  - 未显式设置 `DATABASE_URL` 时，开发态默认写入 `backend/data/issue_aggregator.dev.db`，避免持续污染已跟踪的运行态数据库文件。

[管理流与提交流 E2E 命令]
- Date: 2026-06-14
- Context: Agent 在补管理端批次回归和 GitHub 提交流程脚本时发现
- Category: 测试方法
- Instructions:
  - 管理端建批与审计回归命令为 `cd backend && python3 tests/e2e_admin_batch_flow.py`。
  - GitHub 提交、历史查询和审计回归命令为 `cd backend && python3 tests/e2e_github_submit_flow.py`。

[后台会话认证 E2E 命令]
- Date: 2026-06-15
- Context: Agent 在补后台安全升级登录态回归脚本时发现
- Category: 测试方法
- Instructions:
  - 管理员登录、冷却、会话恢复和登出失效回归命令为 `cd backend && python3 tests/e2e_admin_session_flow.py`。
