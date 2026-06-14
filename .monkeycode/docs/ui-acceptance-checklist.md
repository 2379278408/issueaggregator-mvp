# UI 人工验收清单

## 目标

用于回归检查 Issue Aggregator 当前前端版本的公开提交页和管理工作台，确保布局优化后核心链路、可读性和移动端节奏保持稳定。

## 公开页

- [ ] 首页首屏在桌面端可一次看到标题、反馈类型、关联标识输入和提交主按钮。
- [ ] 首页首屏在窄屏下按钮纵向堆叠，点击区域足够大，没有发生挤压或换行截断。
- [ ] 反馈类型在未选择时显示“请选择反馈类型”，选中后高亮明确。
- [ ] `related_id` 示例 chip 点击后可自动填入并触发查重。
- [ ] 非法 `related_id` 提交时显示中文校验提示。
- [ ] 查重区在“无重复”和“已有重复”两种状态下文案清晰。
- [ ] 历史区默认显示累计结果摘要。
- [ ] 历史区使用关键词和类型筛选后，能显示筛选摘要与“没有匹配结果”空状态。
- [ ] 历史区加载失败时保留错误提示，不覆盖提交成功提示。

## 管理页

- [ ] 未输入 token 时只显示登录卡片，不渲染内部工作台。
- [ ] 进入管理页后，左侧队列、右侧主题画布、草稿区和审计区层级清楚。
- [ ] `pending` 队列支持一键勾选与取消全选。
- [ ] 多条反馈建批后，主题画布显示整批反馈，而不是退化成单条上下文。
- [ ] `grouped` 队列切回批次时，可恢复对应草稿和批次上下文。
- [ ] 草稿区在“未开始 / 待生成 / 待提交 / 已提交”四种状态下文案准确。
- [ ] 草稿标题、正文、保存按钮和提交按钮在窄屏下保持全宽且顺序稳定。
- [ ] 审计事件区支持事件类型、时间范围和关键词组合筛选。
- [ ] 审计区无结果时显示独立空状态。

## 链路回归

- [x] 从 `pending` 选择反馈并创建批次成功。
- [x] 从批次生成草稿成功。
- [x] 保存草稿成功，界面反馈正确。
- [x] 提交 GitHub 成功后状态更新为已提交。
- [x] 切换到 `submitted` 队列可以回看刚提交的记录。

## 自动回归结果

- [x] 前端组件测试覆盖公开页成功态、关联标识复制、历史筛选空状态、管理页草稿提示、审计筛选和批次上下文恢复。
- [x] 后端单元测试覆盖公开反馈限流、AI 草稿兜底、GitHub 提交流程、审计筛选和 HTTP 管理流整链路。
- [x] `python3 tests/e2e_admin_batch_flow.py` 已通过，验证管理端建批和审计事件回写。
- [x] `python3 tests/e2e_github_submit_flow.py` 已通过，验证 GitHub 提交、历史查询和审计记录。

## 验证命令

```bash
# 前端组件测试
cd /workspace/frontend && npm test

# 前端构建
cd /workspace/frontend && npm run build

# 后端单元测试
cd /workspace/backend && python3 -m unittest discover -s tests

# 管理流 E2E
cd /workspace/backend && python3 tests/e2e_admin_batch_flow.py

# GitHub 提交流 E2E
cd /workspace/backend && python3 tests/e2e_github_submit_flow.py

# 补丁格式检查
cd /workspace && git diff --check
```
