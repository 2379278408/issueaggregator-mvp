# IssueAggregator MVP

一个轻量级的 Issue 聚合反馈系统，通过 Vue + FastAPI 技术栈将用户零散的反馈整合为可审核的草稿，并提交结构化的 GitHub Issue。

## 项目描述

IssueAggregator 是一个开源社区治理工具，旨在帮助开发者将来自多渠道的用户反馈（口语化、碎片化）通过 AI 润色和人工审核机制，转化为高质量的 GitHub Issue 提交到官方仓库。

## 核心特性

- **用户反馈收集**: 简洁的前端页面供用户提交原始反馈
- **AI 智能整合**: 调用大模型 API 将多条反馈聚类合并为一条专业 Issue
- **人工审核工作流**: 管理后台支持预览、编辑和确认提交
- **安全提交机制**: 串行提交策略，避免触发 GitHub API 风控
- **实时状态同步**: 前端展示已提交 Issue 的状态和链接

## 技术栈

- **前端**: Vue 3 + Element Plus
- **后端**: FastAPI (Python)
- **数据库**: SQLite (轻量级，无需额外部署)
- **AI 服务**: MiMo API / 其他大模型服务
- **目标平台**: GitHub REST API

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8090
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 环境变量配置

| 变量名 | 说明 | 示例 |
| :--- | :--- | :--- |
| `GITHUB_TOKEN` | GitHub Personal Access Token | `ghp_xxxxx` |
| `MIMO_API_KEY` | MiMo 大模型 API Key | `sk_xxxxx` |
| `TARGET_REPO` | 目标 GitHub 仓库 | `chaitin/MonkeyCode` |

## 项目结构

```
issueaggregator-mvp/
├── backend/              # FastAPI 后端服务
│   ├── main.py          # 主应用入口
│   ├── models.py        # 数据模型
│   ├── api.py           # API 路由
│   └── integrations/    # GitHub/MiMo 集成
├── frontend/            # Vue 3 前端项目
│   ├── src/
│   │   ├── views/       # 页面组件
│   │   └── components/  # 通用组件
│   └── package.json
├── database/            # SQLite 数据库文件
└── README.md
```

## 工作流程图

```
用户提交反馈 -> 后端落库 (pending)
                ↓
管理员点击"整合" -> 调用 MiMo API 分析聚类
                ↓
生成 Draft -> 后台预览/编辑
                ↓
人工确认 -> 串行提交到 GitHub -> 状态更新 (submitted)
```

## 安全策略

- **人工审核**: 所有 Issue 提交前必须经过人工确认
- **频率限制**: 提交接口限制每小时最多 5 次
- **串行提交**: 单次触发仅提交 1 条 Issue，避免并发风控
- **Token 隔离**: GitHub Token 仅存储于服务端环境变量

## 开发计划

- [ ] 基础反馈提交 API
- [ ] 用户端提交页面
- [ ] 管理后台列表功能
- [ ] AI 整合逻辑接入
- [ ] GitHub 提交接口
- [ ] 通知与状态同步

## License

MIT License

## 相关链接

- [上游项目参考](https://github.com/baoweise-bot/aimili-vpngate)
- [LinuxDo 讨论](https://linux.do/)
