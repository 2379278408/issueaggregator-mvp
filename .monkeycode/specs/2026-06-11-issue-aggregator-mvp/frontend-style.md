# Frontend Style Proposal

## Goal

本稿定义 Issue Aggregator MVP 的前端页面风格、信息层级和静态交付约束。

目标如下：

- 页面风格克制、专业、轻量。
- 页面观感接近成熟工具站和开源项目站点。
- 视觉表达避免夸张渐变、悬浮玻璃、营销化口号和模板化 AI 页面痕迹。
- 产物采用纯静态结构，支持打包为 zip 后直接上传使用。

## Delivery Constraint

前端交付采用以下文件结构：

```text
frontend/
  index.html
  admin.html
  styles.css
  app.js
  admin.js
  assets/
```

约束如下：

- 不依赖 Node.js 构建工具。
- 不依赖前端框架运行时。
- 不依赖第三方 CDN 才能启动。
- 页面直接通过浏览器加载静态文件即可使用。
- 与后端接口通过 `/api/*` 通信。

## Style Direction

风格关键词：

- 克制
- 专业
- 安静
- 工具化
- 清晰
- 可信

视觉参考方向：

- 开源项目官网的文档首页质感
- 工程产品控制台的秩序感
- 独立开发者产品的轻量表达

明确避免：

- 大面积霓虹渐变
- 玻璃拟态卡片
- 夸张阴影和漂浮效果
- 过多圆角和糖果色按钮
- 口号式 AI 文案
- 信息块堆叠成通用 SaaS 模板

## Visual System

### Color

主色不追求强品牌攻击性，采用中性深色配一枚冷静蓝色强调。

```css
:root {
  --bg: #f5f7fa;
  --panel: #ffffff;
  --panel-soft: #f8fafc;
  --text: #172033;
  --text-soft: #52607a;
  --line: #d9e0ea;
  --accent: #2f5bea;
  --accent-soft: #e8efff;
  --success: #1f7a4d;
  --warning: #9a6700;
  --danger: #b42318;
}
```

配色原则：

- 页面背景使用浅灰白，减少生硬纯白。
- 主文本使用偏蓝黑色，避免通用纯黑。
- 强调色只用于链接、主按钮、选中态和关键标签。
- 状态色只服务于状态信息，不参与主视觉竞争。

### Typography

推荐字体栈：

```css
font-family: Inter, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
```

字号层级：

- 页面标题：32px / 700
- 区块标题：20px / 600
- 卡片标题：16px / 600
- 正文：15px / 400
- 辅助信息：13px / 400
- 表单标签：13px / 600

文字原则：

- 句子短。
- 标题直接描述功能。
- 少用宣传式副标题。
- 不出现“智能驱动”“高效赋能”“闭环协同”这类空泛表述。

### Spacing

采用 8px 基础网格：

- 页面左右留白：24px 到 40px
- 主区块间距：24px
- 卡片内边距：20px
- 表单项间距：16px
- 标签与正文距离：8px

### Radius and Shadow

- 卡片圆角：12px
- 输入框圆角：10px
- 按钮圆角：10px
- 阴影保持很轻，仅用于区分层级

推荐阴影：

```css
box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 8px 24px rgba(16, 24, 40, 0.04);
```

## Page Structure

### 1. User Page

页面目标：

- 用户先看历史 Issue。
- 用户再决定是否提交。
- 用户提交过程短、直、清楚。

页面结构：

1. 顶部说明区
2. 已提交 Issue 列表区
3. 搜索与筛选区
4. 重复提示区
5. 反馈提交表单区

布局建议：

- 桌面端采用左右双栏。
- 左侧 7 栏展示已提交 Issue 列表。
- 右侧 5 栏展示提交表单和重复提示。
- 移动端改为单栏顺序布局。

### 2. Admin Page

页面目标：

- 高密度信息整理。
- 快速建批次。
- 快速核对 `related_id`。
- 快速审草稿。

页面结构：

1. 顶部状态摘要条
2. 待处理反馈表格
3. 批次信息卡
4. Draft 预览编辑区
5. 历史相同 `related_id` Issue 参考区

布局建议：

- 桌面端采用三段式结构。
- 顶部为摘要条。
- 中部左侧为反馈列表，右侧为批次与历史参考。
- 底部为 Draft 编辑区。

## Component Style

### Header

- 高度紧凑。
- 左侧显示项目名 `Issue Aggregator`。
- 右侧只保留必要导航入口。
- 背景使用白色或半透明白，配细边框。

### Cards

- 卡片标题简短。
- 卡片内部用分隔线替代复杂背景。
- 一张卡只表达一个功能块。

### Issue List

- 每条 Issue 显示标题、Issue 编号、`related_id`、提交时间。
- 标题支持两行截断。
- `related_id` 用细描边标签。
- 外链按钮使用简洁文本链接。

### Search Bar

- 搜索区一行完成。
- 包含关键词输入、类型筛选、`related_id` 输入。
- 不使用巨大搜索框和夸张图标。

### Duplicate Warning

- 使用浅黄色或浅蓝色提示框。
- 文案直说：`已找到相同 related_id 的历史 Issue`。
- 展示匹配 Issue 数量与跳转入口。

### Form

- 表单宽度控制在舒适阅读范围。
- 标签置顶。
- 输入框风格统一。
- 主按钮文案直接使用 `提交反馈`。

### Table

- 后台表格使用细边框与斑马纹弱对比。
- 行高适中。
- 不使用过重的背景块。

### Buttons

- 主按钮：深蓝底白字。
- 次按钮：白底描边。
- 危险按钮：浅红底深红字，仅用于高风险动作。

## Tone of Copy

页面文案采用以下原则：

- 描述事实。
- 直接说明动作。
- 少用感叹句。
- 不夸大系统能力。
- 不把 AI 作为主角。

推荐文案示例：

- 页面标题：`提交反馈前，先看是否已经有人提过`
- 表单说明：`如果这是一个已知主题，请复用已有 related_id。`
- 重复提示：`已存在相同 related_id 的已提交 Issue，你可以先查看历史讨论。`
- 后台按钮：`生成草稿`、`保存修改`、`提交到 GitHub`

## Interaction Rules

- 所有按钮有清晰 hover 和 focus 状态。
- 所有异步提交操作显示 loading 状态。
- 搜索输入变化后 300ms 内触发前端查询。
- 重复提示优先展示，不打断表单编辑。
- 移动端交互不依赖 hover。

## Responsive Strategy

- `>= 1200px` 使用完整多栏布局。
- `768px - 1199px` 采用上下结构和双栏混排。
- `< 768px` 所有区块单列堆叠。
- 移动端优先显示搜索、重复提示、表单，再显示历史 Issue。

## Packaging Guidance

为了满足 zip 上传即用，前端实现阶段应遵守：

- 使用原生 HTML、CSS、JavaScript。
- 图标优先使用内联 SVG。
- 字体使用系统字体栈。
- 页面资源全部相对路径引用。
- 不引入需要构建产物的资源。
- 页面初始化时直接请求 `/api/issues/submitted` 和 `/api/feedback` 相关接口。

## Implementation Recommendation

推荐先做两个静态页面：

- `index.html`：用户提交页
- `admin.html`：后台管理页

推荐先实现的顺序：

1. 全局样式系统 `styles.css`
2. 用户提交页静态结构
3. 已提交 Issue 列表和搜索区
4. 重复提示逻辑
5. 管理后台静态结构
6. Draft 预览编辑区

## Acceptance Standard

当前端完成时，应满足以下标准：

- 直接压缩静态目录即可交付。
- 解压后接上后端接口即可访问。
- 首屏不出现模板化 SaaS 视觉。
- 用户能先看到历史 Issue，再进入提交流程。
- 后台页面以信息效率优先，不追求营销化展示。
