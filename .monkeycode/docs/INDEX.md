# Issue Aggregator 文档索引

## 当前状态

项目处于稳定 MVP 阶段，核心公开提交流程、管理工作台流程、GitHub 提交流程、审计链路和基础工程化能力已经落地。

当前文档按以下结构维护：

- `ARCHITECTURE.md`: 系统结构、数据流、核心模块和运行边界
- `INTERFACES.md`: 前后端路由、API 契约、关键环境变量
- `DEVELOPER_GUIDE.md`: 本地开发、测试、构建、CI、Docker 使用方式
- `RELEASE_CHECKLIST.md`: 最后一次安全推送前的检查顺序
- `ui-acceptance-checklist.md`: UI 人工验收项与自动回归结果
- `improvement-plan.md`: 当前仍待处理的优化项

## 建议阅读顺序

1. 先读 `ARCHITECTURE.md`，建立系统全貌。
2. 再读 `INTERFACES.md`，确认前后端契约和路由入口。
3. 开发或验收前读 `DEVELOPER_GUIDE.md`。
4. 推送前按 `RELEASE_CHECKLIST.md` 执行。

## 项目结论

- 主业务链路已可运行：公开反馈 -> 管理建批 -> 草稿生成/编辑 -> GitHub 提交 -> 审计回看。
- 仓库已具备前后端自动化测试、浏览器级 E2E 命令、Docker Compose 和 GitHub Actions CI。
- 当前剩余工作重点是文档持续同步、窄屏人工验收、超大前端文件拆分和样式模块化。
