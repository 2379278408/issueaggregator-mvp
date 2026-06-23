# 最后一次安全推送检查清单

## 目标

用于最终推送前确认代码、文档、测试和工作区状态一致，降低把脏数据、未验证改动或过期文档推上远端的风险。

## 1. 工作区检查

- [ ] `git status --short` 结果符合预期
- [ ] 没有误提交 `.env`、数据库文件、临时目录、测试产物
- [ ] `.monkeycode/docs/` 与当前实现一致
- [ ] `git diff --check` 无空白问题

## 2. 前端验证

执行目录：`/workspace/frontend`

- [ ] `npm run lint`
- [ ] `npm test`
- [ ] `npm run build`

## 3. 后端验证

执行目录：`/workspace/backend`

- [ ] `python3 -m unittest discover -s tests`
- [ ] `python3 tests/e2e_public_feedback_guardrails.py`
- [ ] `python3 tests/e2e_admin_batch_flow.py`
- [ ] `python3 tests/e2e_github_submit_flow.py`
- [ ] `python3 tests/e2e_admin_session_flow.py`

## 4. 发布前人工确认

- [ ] 公开页窄屏布局已人工看过
- [ ] 管理台三栏与草稿区窄屏布局已人工看过
- [ ] 管理登录、建批、生成草稿、保存、提交、审计回看链路已确认
- [ ] 如需真实 GitHub 提交，目标仓库和令牌已确认正确

## 5. 推送建议顺序

1. 先完成验证命令。
2. 再检查 `git status` 和 `git diff`。
3. 最后执行提交和推送。

当前仓库已经具备自动化测试和 CI，最后一次安全推送的核心价值在于确认“文档、代码、运行入口、验收结论”四者一致。
