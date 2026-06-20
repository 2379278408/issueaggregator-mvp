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

[后台浏览器验收命令]
- Date: 2026-06-17
- Context: Agent 在补管理工作台浏览器端到端验收脚本时发现
- Category: 测试方法
- Instructions:
  - 浏览器级后台验收命令为 `cd frontend && ADMIN_E2E_URL=<后台预览地址> ADMIN_E2E_USERNAME=<用户名> ADMIN_E2E_PASSWORD=<密码> npm run e2e:admin`。
  - 若需要把草稿真实提交到 GitHub，可额外附加 `ADMIN_E2E_SUBMIT=true`。

[全链路浏览器 E2E 命令]
- Date: 2026-06-18
- Context: Agent 在补全链路浏览器端到端验收脚本（反馈→整理→AI草稿→编辑→保存→审计）时发现
- Category: 测试方法
- Instructions:
  - 全链路浏览器 E2E 命令为 `cd frontend && PIPELINE_E2E_URL=<API地址> PIPELINE_E2E_ADMIN_ROUTE=<路由slug> npm run e2e:pipeline`。
  - 若需真实提交 GitHub，附加 `PIPELINE_E2E_SUBMIT=true`。
  - 公开反馈 API 有 IP 日限流 5 次，脚本内置限流回退机制。
  - 队列为空时脚本自动切换到已分组队列继续测试。

[e2e-pipeline skill]
- Date: 2026-06-18
- Context: Agent 创建 e2e-pipeline skill 用于封装 E2E 测试工作流
- Category: 工作流协作
- Instructions:
  - 当需要浏览器级 E2E 测试时，使用 `/e2e-pipeline` skill。
  - Skill 包含 SKILL.md（快速启动、配置参考、模式参考）、references/testing-guide.md（详细容错模式、断言模式）、scripts/run-e2e.sh（串行执行单测→构建→E2E）。

[goal skill]
- Date: 2026-06-19
- Context: Agent 安装 goal skill 提供会话级目标驱动开发能力
- Category: 工作流协作
- Instructions:
  - 使用 `/goal <objective> --verify "<cmd>" --max-turns N` 设定目标驱动开发循环。
  - 每轮自动 checkpoint、验证、反循环检测（3 轮无进展自动暂停）。
  - 支持 `/goal status` / `pause` / `resume` / `clear`。
  - 状态文件位于 `.monkeycode/goal/current.json`。
  - goal-state.sh 位于 `.opencode/skills/goal/goal-state.sh`。
