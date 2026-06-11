# Frontend Vue Plan

## Goal

本稿把当前前端方案切换为 Vue 实现方案，同时保持以下原则：

- 风格克制、专业、轻量。
- 页面避免通用 AI 模板感。
- 开发阶段使用 Vue 组件化开发。
- 交付阶段输出构建后的静态目录，可直接压缩为 zip 上传部署。

## Delivery Strategy

开发技术栈：

- Vue 3
- Vite
- Vue Router
- 原生 CSS

交付方式：

- 本地开发和联调使用 Vue 工程。
- 最终交付使用 `npm run build` 生成的 `dist/` 目录。
- 将 `dist/` 目录压缩为 zip 后即可上传到服务器静态目录。

这意味着：

- 你平时拿到的是标准 Vue 项目，便于继续改。
- 真正部署时上传的是纯静态产物，便于即用。

## Project Structure

推荐项目结构如下：

```text
frontend/
  public/
  src/
    assets/
    components/
      layout/
      issue/
      feedback/
      admin/
      common/
    pages/
      UserHomePage.vue
      AdminWorkbenchPage.vue
    router/
      index.ts
    services/
      api.ts
      feedback.ts
      issues.ts
      drafts.ts
    stores/
      feedback.ts
      issues.ts
      admin.ts
    styles/
      tokens.css
      base.css
      layout.css
      components.css
    App.vue
    main.ts
  index.html
  vite.config.ts
  package.json
```

## Vite Configuration

Vite 配置要求：

- 开发环境添加 `allowedHosts: ['.monkeycode-ai.online']`
- 开发环境配置 `/api` 反向代理到后端服务
- 构建输出目录固定为 `dist`
- 构建产物使用相对稳定的资源路径

建议配置目标：

```ts
server: {
  allowedHosts: ['.monkeycode-ai.online'],
  proxy: {
    '/api': {
      target: 'http://localhost:3001',
      changeOrigin: true,
    },
  },
}
```

## Route Design

只保留两个一级页面：

- `/`：用户提交页
- `/admin`：管理后台页

MVP 阶段不引入复杂嵌套路由。

## Page Design

### 1. `UserHomePage.vue`

页面职责：

- 展示已提交 Issue 列表
- 提供搜索和筛选
- 提供 `related_id` 实时重复提示
- 提供反馈提交表单

页面分区：

1. 顶部引导区
2. Issue 搜索和筛选栏
3. 已提交 Issue 列表
4. 重复提示卡
5. 反馈提交表单

推荐组件拆分：

- `AppShell.vue`
- `PageHeader.vue`
- `SubmittedIssueFilters.vue`
- `SubmittedIssueList.vue`
- `SubmittedIssueCard.vue`
- `RelatedIdWarning.vue`
- `FeedbackForm.vue`
- `FormField.vue`

### 2. `AdminWorkbenchPage.vue`

页面职责：

- 查看待处理反馈
- 勾选反馈组成批次
- 查看 `related_id` 分布
- 触发 Draft 生成
- 编辑 Draft
- 查看同 `related_id` 的历史 Issue

页面分区：

1. 状态摘要条
2. 待处理反馈表格
3. 批次信息侧栏
4. Draft 编辑器
5. 历史 Issue 参考区

推荐组件拆分：

- `StatusSummaryBar.vue`
- `PendingFeedbackTable.vue`
- `FeedbackRow.vue`
- `BatchSummaryPanel.vue`
- `RelatedIdDistribution.vue`
- `DraftEditorPanel.vue`
- `HistoricalIssuePanel.vue`
- `ActionToolbar.vue`

## Component Design Principles

组件层级遵守以下原则：

- 页面组件负责布局和调用 store。
- 业务组件负责列表、表单、预览、提示。
- 通用组件只处理按钮、输入框、标签、卡片、空状态。
- 不过早抽象复杂组件库。

这样可以保持：

- 初版实现快。
- 风格统一。
- 后续替换样式成本低。

## State Strategy

MVP 推荐使用轻量状态管理。

可选方案：

1. 页面内 `ref` 和 `computed`
2. 使用 Pinia

我的建议：

- 页面本地状态用于表单、筛选、loading。
- Pinia 用于已提交 Issue 列表、待处理反馈列表、Draft 数据。

建议 store：

- `issuesStore`
- `feedbackStore`
- `adminStore`

## API Layer

前端所有接口调用统一走 `services/api.ts`，避免在组件内直接写请求。

建议方法：

- `getSubmittedIssues(params)`
- `searchSubmittedIssues(params)`
- `createFeedback(payload)`
- `getPendingFeedback()`
- `createDraftBatch(payload)`
- `integrateDraftBatch(id)`
- `getDraft(id)`
- `updateDraft(id, payload)`
- `submitDraft(id)`

## Visual Implementation Rules

Vue 实现阶段继续沿用 `frontend-style.md` 的视觉规则，重点如下：

- 不使用组件库默认的厚重控件风格。
- 不使用炫技动画和营销化头图区块。
- 不使用“AI 生成”“智能助理”式主视觉语言。
- 保持卡片、表单、表格、标签的统一样式。

## Styling Strategy

样式组织推荐如下：

- `tokens.css`：颜色、字体、圆角、阴影、间距 token
- `base.css`：重置、排版、基础元素
- `layout.css`：容器、栅格、页面结构
- `components.css`：按钮、卡片、标签、表单、表格

原因：

- 打包后没有样式依赖风险。
- 全局样式体积可控。
- 便于后续在服务器上快速改一处样式。

## Anti AI-Look Rules

为了去掉 AI 味道，前端实现时遵守以下规则：

- 首页标题使用任务导向语言，不使用口号。
- 页面区块围绕真实任务流程排列，不堆砌展示模块。
- 卡片数量控制在必要范围内。
- 图标只在帮助理解时出现。
- 留白自然，不追求“设计稿摆拍感”。
- 文案像工具，不像广告。

推荐页面标题：

- 用户页：`提交反馈前，先检查是否已有相关 Issue`
- 后台页：`待处理反馈与草稿工作台`

## Build and Deploy Flow

标准流程如下：

1. 本地执行 `npm install`
2. 本地执行 `npm run dev`
3. 联调 `/api` 接口
4. 执行 `npm run build`
5. 将 `dist/` 压缩为 zip
6. 上传 zip 并解压到服务器静态目录

如果服务器由后端托管静态资源：

- 将 `dist/` 放到后端静态目录
- 后端继续代理 `/api`

## Acceptance Standard

Vue 版前端完成后，应满足以下标准：

- 开发期是标准 Vue 项目。
- 产出期是可直接部署的静态目录。
- 用户页重点突出历史 Issue 与重复提示。
- 后台页重点突出反馈处理效率。
- 页面整体没有模板化 AI 产品视觉。
- `dist/` 压缩后可直接上传使用。

## Recommended Next Step

下一步直接开始实现 Vue 项目骨架，并优先完成：

1. `Vite + Vue 3` 初始化
2. `vite.config.ts` 代理和 `allowedHosts`
3. 路由与页面骨架
4. 全局样式 token
5. 用户页静态布局
6. 后台页静态布局
