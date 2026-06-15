<template>
  <AppShell
    title="Issue Intake"
    description="提交反馈，生成可追踪 Issue。"
  >
    <section class="intake-studio">
      <header class="intake-hero">
        <div>
          <p class="eyebrow">Public Intake</p>
          <h2>提交清晰反馈</h2>
          <p>填写标识、现象和影响。相同主题会自动提示。</p>
        </div>
        <div class="intake-hero__metrics">
          <span>已提交 Issue</span>
          <strong>{{ submittedIssueTotal }}</strong>
          <small>公开反馈会自动聚合成可追踪的 GitHub Issue。</small>
        </div>
      </header>

      <section class="intake-grid">
        <article class="feedback-composer">
          <div class="studio-section-head">
            <div>
              <span>Composer</span>
              <h3>反馈内容</h3>
            </div>
            <p>先判断类型和主题，再补正文，减少无效填写。</p>
          </div>

          <form class="composer-form" @submit.prevent="submitFeedback">
            <section
              class="composer-stage feedback-type-picker"
              :class="{ 'composer-stage--ready': Boolean(form.type), 'feedback-type-picker--ready': Boolean(form.type) }"
              aria-labelledby="feedback-type-title"
            >
              <div class="feedback-type-picker__head">
                <div>
                  <span id="feedback-type-title">Step 1 / 反馈类型</span>
                  <strong>{{ selectedTypeLabel || '请选择反馈类型' }}</strong>
                </div>
                <small>主动选择后再提交，便于后台按类型聚合。</small>
              </div>
              <div class="feedback-type-grid" role="radiogroup" aria-label="反馈类型">
                <button
                  v-for="option in feedbackTypeOptions"
                  :key="option.value"
                  class="feedback-type-card"
                  :class="{ 'feedback-type-card--active': form.type === option.value }"
                  type="button"
                  role="radio"
                  :aria-checked="form.type === option.value"
                  @click="selectFeedbackType(option.value)"
                >
                  <span>{{ option.label }}</span>
                  <small>{{ option.description }}</small>
                </button>
              </div>
            </section>

            <section class="composer-stage composer-stage--compact" :class="{ 'composer-stage--ready': hasValidRelatedId }">
              <div class="studio-section-head studio-section-head--compact">
                <div>
                  <span>Step 2 / Topic Key</span>
                  <h3>关联标识与查重</h3>
                </div>
                <p>先确认这是哪个页面、流程或组件，系统会帮你对照已有 Issue。</p>
              </div>

            <div class="composer-row composer-row--single">
              <label class="field">
                <span>关联标识</span>
                <input v-model="form.related_id" class="input" placeholder="editor-copy-button" @blur="handleRelatedIdBlur" />
                <small class="field-helper">用小写英文、数字和短横线，例如 github-submit-flow；空格和下划线会自动转成短横线。</small>
              </label>
            </div>

            <div class="composer-support-row">
              <div class="related-id-guide" aria-label="关联标识填写示例">
                <div>
                  <strong>怎么填关联标识</strong>
                  <p>按页面、组件、接口或业务流程命名，使用小写英文、数字和短横线。</p>
                </div>
                <div class="related-id-examples">
                  <button
                    class="related-id-chip related-id-chip--primary"
                    type="button"
                    @click="applyRelatedExample(primaryRelatedExample)"
                  >
                    {{ primaryRelatedExample }}
                  </button>
                  <button
                    v-for="example in secondaryRelatedExamples"
                    :key="example"
                    class="related-id-chip"
                    type="button"
                    @click="applyRelatedExample(example)"
                  >
                    {{ example }}
                  </button>
                </div>
              </div>

              <section class="duplicate-panel duplicate-panel--inline" :class="`duplicate-panel--${duplicateStateTone}`">
                <div class="studio-section-head studio-section-head--compact">
                  <div>
                    <span>Duplicate</span>
                    <h3>{{ duplicateIssues.length ? duplicatePanelTitle : '查重' }}</h3>
                  </div>
                </div>
                <div class="duplicate-panel__status">
                  <span class="duplicate-panel__badge">{{ duplicateStatusLabel }}</span>
                  <strong>{{ duplicateActionTitle }}</strong>
                </div>
                <p v-if="duplicateIssues.length">{{ duplicateSummary }}</p>
                <p v-else>{{ duplicateHint }}</p>
                <p class="duplicate-panel__recommendation">{{ duplicateActionHint }}</p>
                <ul v-if="duplicateIssues.length" class="duplicate-list duplicate-list--studio">
                  <li v-for="issue in duplicateIssues" :key="issue.issue_number">
                    <a :href="issue.issue_url" target="_blank" rel="noreferrer">#{{ issue.issue_number }} {{ issue.title }}</a>
                  </li>
                </ul>
              </section>
            </div>
            </section>

            <section class="composer-stage composer-stage--compact quick-template-panel" aria-label="快捷反馈模板">
              <div class="studio-section-head studio-section-head--compact">
                <div>
                  <span>Quick Start</span>
                  <h3>快捷模板</h3>
                </div>
                <p>常见场景可以一键带入，减少从零组织内容的时间。</p>
              </div>
              <div class="quick-template-grid">
                <button
                  v-for="template in quickTemplates"
                  :key="template.label"
                  class="quick-template-card"
                  :class="{ 'quick-template-card--active': selectedTemplateKey === template.key }"
                  type="button"
                  @click="applyQuickTemplate(template.key)"
                >
                  <strong>{{ template.label }}</strong>
                  <span>{{ template.description }}</span>
                </button>
              </div>
            </section>

            <section class="composer-stage composer-stage--compact" :class="{ 'composer-stage--ready': Boolean(form.raw_content.trim()) }">
              <div class="studio-section-head studio-section-head--compact">
                <div>
                  <span>Step 3 / Core Message</span>
                  <h3>核心反馈</h3>
                </div>
                <p>优先写清触发场景、实际现象和影响范围，够用就能提交。</p>
              </div>

              <label class="field field--full composer-main-field">
                <span>反馈内容</span>
                <textarea v-model="form.raw_content" class="textarea textarea--editor" rows="8" placeholder="描述触发场景、具体表现和影响范围"></textarea>
              </label>

              <details class="composer-details">
                <summary>补充细节（可选）</summary>
                <div class="composer-row">
                  <label class="field">
                    <span>期望行为</span>
                    <textarea v-model="form.expected_behavior" class="textarea" rows="4" placeholder="希望系统如何表现"></textarea>
                  </label>
                  <label class="field">
                    <span>实际行为</span>
                    <textarea v-model="form.actual_behavior" class="textarea" rows="4" placeholder="现在实际发生了什么"></textarea>
                  </label>
                </div>
                <div class="context-capture">
                  <div class="context-capture__head">
                    <strong>上下文信息</strong>
                    <span>{{ contextSummaryText }}</span>
                  </div>
                  <div class="composer-row">
                    <label class="field">
                      <span>页面链接</span>
                      <input v-model="form.page_url" class="input" placeholder="https://example.com/settings" />
                    </label>
                    <label class="field">
                      <span>页面标题</span>
                      <input v-model="form.page_title" class="input" placeholder="反馈页面标题" />
                    </label>
                  </div>
                  <label class="field field--full">
                    <span>运行环境</span>
                    <textarea
                      v-model="form.environment_context"
                      class="textarea"
                      rows="3"
                      placeholder="浏览器、系统、窗口尺寸或触发环境"
                    ></textarea>
                    <small class="field-helper">默认会带入当前页面 URL 和浏览器环境，你可以按需补充或删改。</small>
                  </label>
                </div>
              </details>
            </section>

            <div v-if="submitMessage" class="feedback-message field--full">{{ submitMessage }}</div>
            <section v-if="lastSubmission" class="submission-summary-card" aria-label="最近一次提交摘要">
              <div>
                <span class="submission-summary-card__eyebrow">最近一次提交</span>
                <strong>{{ lastSubmission.related_id }}</strong>
                <p>
                  {{ lastSubmission.typeLabel }}反馈已进入待整理队列，反馈编号 {{ lastSubmission.id }}。
                  <span v-if="lastSubmission.created_at">提交时间 {{ lastSubmission.created_at }}</span>
                </p>
              </div>
              <div class="submission-summary-card__actions">
                <button class="button button--quiet button--compact" type="button" @click="copyRelatedId">
                  {{ copyStateLabel }}
                </button>
                <button class="button button--secondary button--compact" type="button" @click="viewRelatedHistory">
                  查看同标识历史
                </button>
              </div>
            </section>
            <div class="composer-actions">
              <span>
                {{ submissionReadinessText }}
                <small class="composer-actions__note">同一 IP 每天最多提交 5 次反馈。</small>
              </span>
              <button class="button" type="submit">{{ submitting ? '提交中...' : '提交反馈' }}</button>
            </div>
          </form>
        </article>

          <aside class="intake-inspector">
            <section class="intake-checklist-panel">
              <div class="inspector-section-head">
                <span>Readiness</span>
                <strong>提交前检查</strong>
              </div>
              <div class="intake-checklist">
                <article class="intake-checklist__item" :class="{ 'is-ready': Boolean(form.type) }">
                  <strong>类型</strong>
                <span>{{ selectedTypeLabel || '待选择' }}</span>
              </article>
              <article class="intake-checklist__item" :class="{ 'is-ready': hasValidRelatedId }">
                <strong>标识</strong>
                <span>{{ normalizedRelatedId || '待输入' }}</span>
              </article>
              <article class="intake-checklist__item" :class="{ 'is-ready': Boolean(form.raw_content.trim()) }">
                <strong>正文</strong>
                <span>{{ form.raw_content.trim() ? '已填写核心描述' : '待填写' }}</span>
              </article>
              <article class="intake-checklist__item" :class="{ 'is-ready': hasContextInfo }">
                <strong>上下文</strong>
                <span>{{ hasContextInfo ? contextSummaryText : '已留空' }}</span>
              </article>
            </div>
          </section>

            <section class="history-panel">
              <div class="studio-section-head">
                <div>
                  <span>History</span>
                  <h3>历史记录</h3>
                </div>
                <p>{{ historySummaryTitle }}</p>
              </div>
              <div class="history-search">
                <input v-model="filters.keyword" class="input" placeholder="搜索标识或关键词" />
              <select v-model="filters.type" class="select">
                <option value="all">全部</option>
                <option value="bug">缺陷</option>
                <option value="feature">新功能</option>
                <option value="enhancement">优化</option>
                <option value="question">问题</option>
              </select>
              <button class="button button--quiet" type="button" @click="loadSubmittedIssues">搜索</button>
              </div>
              <div class="history-inline-summary">{{ historySummaryHint }}</div>
              <div v-if="historyMessage" class="feedback-message feedback-message--subtle">{{ historyMessage }}</div>
            <div class="history-list">
              <article v-for="issue in submittedIssues" :key="issue.issue_number" class="history-card">
                <div class="history-card__meta">
                  <span class="history-card__type">{{ getTypeLabel(issue.type) }}</span>
                  <strong class="history-card__number">#{{ issue.issue_number }}</strong>
                </div>
                <a :href="issue.issue_url" target="_blank" rel="noreferrer">{{ issue.title }}</a>
                <span class="history-card__related">{{ issue.related_id }}</span>
              </article>
              <div v-if="!submittedIssues.length && !issuesLoading" class="empty-state">
                <strong class="empty-state__title">{{ historyEmptyTitle }}</strong>
                <span class="empty-state__hint">{{ historyEmptyHint }}</span>
              </div>
              <div v-if="issuesLoading" class="empty-state empty-state--loading">正在加载...</div>
            </div>
          </section>
        </aside>
      </section>
    </section>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

import AppShell from '../components/layout/AppShell.vue'
import {
  apiGet,
  apiPost,
  buildPublicApiPath,
  buildSubmittedIssueSearch,
  type FeedbackCreatePayload,
  type PaginatedResponse,
  type SubmittedIssue,
} from '../services/api'

const typeLabelMap: Record<string, string> = {
  bug: '缺陷',
  feature: '新功能',
  enhancement: '优化',
  question: '问题',
  mixed: '混合',
}

const feedbackTypeOptions = [
  { value: 'bug', label: '缺陷', description: '功能异常、报错、结果不符合预期' },
  { value: 'feature', label: '新功能', description: '希望新增的能力或完整流程' },
  { value: 'enhancement', label: '优化', description: '体验、性能、文案或交互改进' },
  { value: 'question', label: '问题', description: '需要确认规则、边界或使用方式' },
]

const quickTemplates = [
  {
    key: 'broken-flow',
    label: '流程异常',
    description: '页面或接口流程被中断、卡住、跳错页',
    type: 'bug',
    rawContent: '在执行某个操作流程时，页面出现异常中断或卡住，影响继续完成任务。',
    expectedBehavior: '流程应当连续完成，并返回明确的结果。',
    actualBehavior: '执行到中间步骤时出现异常，无法继续完成当前任务。',
  },
  {
    key: 'experience-upgrade',
    label: '体验优化',
    description: '操作路径太长、信息层级不清、交互不够顺手',
    type: 'enhancement',
    rawContent: '当前页面完成任务需要经过较多步骤，信息分布分散，影响处理效率。',
    expectedBehavior: '高频操作应更直接，关键上下文应保持可见。',
    actualBehavior: '用户需要频繁滚动或切换视线，才能完成一次完整操作。',
  },
  {
    key: 'new-capability',
    label: '新增能力',
    description: '已有流程缺少关键功能，需要补上完整能力',
    type: 'feature',
    rawContent: '当前流程缺少一个关键能力，导致需要依赖额外手工操作才能完成目标。',
    expectedBehavior: '系统应直接提供这项能力，减少额外手工步骤。',
    actualBehavior: '当前版本没有对应入口或能力，任务无法直接完成。',
  },
]

const relatedExamples = ['github-submit-flow', 'editor-copy-button', 'login-timeout', 'mobile-navbar']
const primaryRelatedExample = relatedExamples[0]
const secondaryRelatedExamples = relatedExamples.slice(1)
const relatedIdPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

const submittedIssues = ref<SubmittedIssue[]>([])
const submittedIssueTotal = ref(0)
const issuesLoading = ref(false)
const duplicateIssues = ref<SubmittedIssue[]>([])
const duplicateLookupState = ref<'idle' | 'loading' | 'empty' | 'error'>('idle')
const duplicateMatchKind = ref<'exact' | 'related'>('exact')
const duplicateLookupErrorMessage = ref('')
const selectedTemplateKey = ref('')
const submitting = ref(false)
const submitMessage = ref('')
const historyMessage = ref('')
const lastSubmission = ref<{ id: string; related_id: string; typeLabel: string; created_at: string } | null>(null)
const copyStateLabel = ref('复制关联标识')
let preserveSubmitMessageOnReset = false
let duplicateLookupTimer: ReturnType<typeof setTimeout> | null = null
let duplicateLookupRequestId = 0
let suppressDuplicateLookupWatch = false
let suppressTemplateSelectionWatch = false

const filters = reactive({
  keyword: '',
  type: 'all',
})

const form = reactive<FeedbackCreatePayload>({
  type: '',
  related_id: '',
  raw_content: '',
  expected_behavior: '',
  actual_behavior: '',
  page_url: '',
  page_title: '',
  environment_context: '',
})

const normalizedRelatedId = computed(() => form.related_id.trim())
const selectedTypeLabel = computed(() => (form.type ? getTypeLabel(form.type) : ''))
const hasContextInfo = computed(() => Boolean(form.page_url?.trim() || form.page_title?.trim() || form.environment_context?.trim()))
const contextSummaryText = computed(() => {
  const segments = []
  if (form.page_url?.trim()) {
    segments.push('已带页面链接')
  }
  if (form.page_title?.trim()) {
    segments.push('已带页面标题')
  }
  if (form.environment_context?.trim()) {
    segments.push('已带运行环境')
  }
  return segments.length ? segments.join(' / ') : '当前未附加上下文'
})
const hasHistoryFilters = computed(() => Boolean(filters.keyword.trim()) || filters.type !== 'all')
const historySectionHint = computed(() => (hasHistoryFilters.value ? '按关键词或类型缩小结果范围。' : '查看最近聚合后的 GitHub Issue。'))
const historySummaryTitle = computed(() => {
  if (issuesLoading.value) {
    return '正在刷新历史记录'
  }
  if (hasHistoryFilters.value) {
    return `当前结果 ${submittedIssues.value.length} 条`
  }
  return `最近记录 ${submittedIssues.value.length} 条`
})
const historySummaryHint = computed(() => {
  if (hasHistoryFilters.value) {
    const parts = []
    if (filters.keyword.trim()) {
      parts.push(`关键词 ${filters.keyword.trim()}`)
    }
    if (filters.type !== 'all') {
      parts.push(`类型 ${getTypeLabel(filters.type)}`)
    }
    return parts.length ? `已按 ${parts.join(' / ')} 筛选` : '已应用筛选'
  }
  return `累计已提交 ${submittedIssueTotal.value} 条 Issue`
})
const historyEmptyTitle = computed(() => (hasHistoryFilters.value ? '没有匹配结果' : '暂无历史记录'))
const historyEmptyHint = computed(() => {
  if (hasHistoryFilters.value) {
    return '调整关键词或类型后重新搜索，或者查看全部历史记录。'
  }
  return '搜索结果会在这里展示，便于确认同类问题是否已经进入 GitHub。'
})
const hasValidRelatedId = computed(() => isValidRelatedId(normalizedRelatedId.value))
const duplicateHint = computed(() => {
  if (!normalizedRelatedId.value) {
    return '输入关联标识后显示同主题 Issue，提交前可快速判断是否已经有人反馈。'
  }
  if (!isValidRelatedId(normalizedRelatedId.value)) {
    return '关联标识格式需为小写英文、数字和短横线。'
  }
  if (duplicateLookupState.value === 'loading') {
    return '正在检查同主题 Issue...'
  }
  if (duplicateLookupState.value === 'empty') {
    return '当前还没有找到同标识的已提交 Issue。'
  }
  if (duplicateLookupState.value === 'error') {
    return duplicateLookupErrorMessage.value || '同主题检查失败，请稍后重试。'
  }
  return '输入关联标识后显示同主题 Issue，提交前可快速判断是否已经有人反馈。'
})
const duplicatePanelTitle = computed(() => (duplicateMatchKind.value === 'exact' ? '发现同标识' : '发现相近主题'))
const duplicateSummary = computed(() => {
  const matchLabel = duplicateMatchKind.value === 'exact' ? '同标识' : '相近主题'
  return `已有 ${duplicateIssues.value.length} 条${matchLabel}记录。`
})
const duplicateStateTone = computed(() => {
  if (duplicateIssues.value.length) {
    return duplicateMatchKind.value === 'exact' ? 'match' : 'related'
  }
  if (!normalizedRelatedId.value) {
    return 'idle'
  }
  if (!hasValidRelatedId.value) {
    return 'warning'
  }
  if (duplicateLookupState.value === 'loading') {
    return 'loading'
  }
  if (duplicateLookupState.value === 'error') {
    return 'error'
  }
  if (duplicateLookupState.value === 'empty') {
    return 'clear'
  }
  return 'idle'
})
const duplicateStatusLabel = computed(() => {
  if (duplicateIssues.value.length) {
    return duplicateMatchKind.value === 'exact' ? '已命中' : '有相近项'
  }
  if (!normalizedRelatedId.value) {
    return '待输入'
  }
  if (!hasValidRelatedId.value) {
    return '需修正'
  }
  if (duplicateLookupState.value === 'loading') {
    return '检查中'
  }
  if (duplicateLookupState.value === 'error') {
    return '检查失败'
  }
  if (duplicateLookupState.value === 'empty') {
    return '可继续'
  }
  return '待输入'
})
const duplicateActionTitle = computed(() => {
  if (duplicateIssues.value.length) {
    return duplicateMatchKind.value === 'exact' ? '先看已有记录，再决定是否补充新证据。' : '先确认是否属于同一主题，再决定是否继续提交。'
  }
  if (!normalizedRelatedId.value) {
    return '先填关联标识，系统会自动对照已有 Issue。'
  }
  if (!hasValidRelatedId.value) {
    return '先把标识格式修正为小写英文、数字和短横线。'
  }
  if (duplicateLookupState.value === 'loading') {
    return '系统正在比对同主题记录。'
  }
  if (duplicateLookupState.value === 'error') {
    return '查重暂时不可用，建议稍后重试一次。'
  }
  if (duplicateLookupState.value === 'empty') {
    return '当前没有找到同主题记录。'
  }
  return '先填关联标识，系统会自动对照已有 Issue。'
})
const duplicateActionHint = computed(() => {
  if (duplicateIssues.value.length) {
    return duplicateMatchKind.value === 'exact'
      ? '如果只是补充复现路径、截图或影响范围，优先复用现有主题，避免重复提单。'
      : '如果标题和场景高度接近，优先查看已有 Issue，确认能否合并到同一主题。'
  }
  if (!normalizedRelatedId.value) {
    return '建议按页面、流程或组件命名，例如 github-submit-flow。'
  }
  if (!hasValidRelatedId.value) {
    return '格式正确后会自动开始查重，无需额外点击。'
  }
  if (duplicateLookupState.value === 'loading') {
    return '检查完成前可以先补正文，结果会自动更新在这里。'
  }
  if (duplicateLookupState.value === 'error') {
    return '如果你确认问题紧急，可以先完成正文填写，稍后再重新检查一次。'
  }
  if (duplicateLookupState.value === 'empty') {
    return '可以继续填写正文并提交，后台会按主题继续聚合。'
  }
  return '建议按页面、流程或组件命名，例如 github-submit-flow。'
})
const submissionReadinessText = computed(() => {
  if (!form.type) {
    return '先选择反馈类型'
  }
  if (!normalizedRelatedId.value) {
    return '再输入关联标识'
  }
  if (!hasValidRelatedId.value) {
    return '关联标识格式需为小写英文、数字和短横线'
  }
  if (!form.raw_content.trim()) {
    return '最后补一段核心描述即可提交'
  }
  return `已准备提交：${selectedTypeLabel.value} / ${normalizedRelatedId.value}`
})
function normalizeRelatedId(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_\s]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function isValidRelatedId(value: string): boolean {
  return relatedIdPattern.test(value)
}

function getTypeLabel(type: string): string {
  return typeLabelMap[type] || type
}

function normalizePageUrl(value: string): string {
  const normalized = value.trim()
  if (!normalized) {
    return ''
  }

  try {
    const parsed = new URL(normalized, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
    const isAbsolute = /^[a-zA-Z][a-zA-Z\d+.-]*:/.test(normalized)
    const isRootRelative = normalized.startsWith('/')
    const hasNetworkLocation = Boolean(parsed.protocol && parsed.host)

    if (isAbsolute && hasNetworkLocation) {
      return `${parsed.origin}${parsed.pathname || '/'}`.slice(0, 1000)
    }
    if (isRootRelative) {
      return `${parsed.pathname || '/'}`.slice(0, 1000)
    }
  } catch {
    return normalized.split('#', 1)[0].split('?', 1)[0].slice(0, 1000)
  }

  return normalized.split('#', 1)[0].split('?', 1)[0].slice(0, 1000)
}

function clampOptionalText(value: string | undefined, maxLength: number): string {
  return (value || '').trim().slice(0, maxLength)
}

function buildDefaultContext(): Pick<FeedbackCreatePayload, 'page_url' | 'page_title' | 'environment_context'> {
  if (typeof window === 'undefined') {
    return {
      page_url: '',
      page_title: '',
      environment_context: '',
    }
  }

  const contextParts = []
  if (navigator.language?.trim()) {
    contextParts.push(`language=${clampOptionalText(navigator.language, 64)}`)
  }
  if (navigator.platform?.trim()) {
    contextParts.push(`platform=${clampOptionalText(navigator.platform, 160)}`)
  }
  if (window.innerWidth && window.innerHeight) {
    contextParts.push(`viewport=${window.innerWidth}x${window.innerHeight}`)
  }

  return {
    page_url: normalizePageUrl(window.location.href),
    page_title: clampOptionalText(document.title, 200),
    environment_context: clampOptionalText(contextParts.join(' | '), 500),
  }
}

function hydrateContextDefaults(force = false): void {
  const defaults = buildDefaultContext()
  if (force || !form.page_url?.trim()) {
    form.page_url = defaults.page_url || ''
  }
  if (force || !form.page_title?.trim()) {
    form.page_title = defaults.page_title || ''
  }
  if (force || !form.environment_context?.trim()) {
    form.environment_context = defaults.environment_context || ''
  }
}

function selectFeedbackType(type: string): void {
  form.type = type
  submitMessage.value = ''
}

function applyQuickTemplate(templateKey: string): void {
  const template = quickTemplates.find((item) => item.key === templateKey)
  if (!template) {
    return
  }

  suppressTemplateSelectionWatch = true
  selectedTemplateKey.value = template.key
  form.type = template.type
  form.raw_content = template.rawContent
  form.expected_behavior = template.expectedBehavior
  form.actual_behavior = template.actualBehavior
  submitMessage.value = ''
  void nextTick(() => {
    suppressTemplateSelectionWatch = false
  })
}

async function loadSubmittedIssues(): Promise<void> {
  issuesLoading.value = true
  historyMessage.value = ''
  try {
    const response = await apiGet<PaginatedResponse<SubmittedIssue>>(buildSubmittedIssueSearch(filters))
    if (response.success) {
      submittedIssues.value = response.data.items
      submittedIssueTotal.value = response.data.total ?? response.data.items.length
    } else {
      submittedIssues.value = []
      historyMessage.value = response.message || '已提交 Issue 加载失败，请稍后重试。'
    }
  } catch {
    submittedIssues.value = []
    historyMessage.value = '已提交 Issue 加载失败，请稍后重试。'
  } finally {
    issuesLoading.value = false
  }
}

function buildRelatedKeywordCandidates(relatedId: string): string[] {
  const segments = relatedId.split('-').filter((segment) => segment.length >= 4)
  const prefixes = segments
    .map((_, index) => segments.slice(0, segments.length - index).join('-'))
    .filter((segment) => segment && segment !== relatedId)

  return [...new Set([...prefixes, ...segments.filter((segment) => segment !== relatedId)])]
}

async function fetchSubmittedIssues(params: { related_id?: string; keyword?: string }): Promise<SubmittedIssue[]> {
  const response = await apiGet<PaginatedResponse<SubmittedIssue>>(buildSubmittedIssueSearch(params))
  if (!response.success) {
    throw new Error(response.message || '同主题检查失败，请稍后重试。')
  }
  return response.data.items
}

function resetDuplicateLookupState(): void {
  duplicateLookupRequestId += 1
  duplicateIssues.value = []
  duplicateLookupState.value = 'idle'
  duplicateMatchKind.value = 'exact'
  duplicateLookupErrorMessage.value = ''
}

function clearDuplicateLookupTimer(): void {
  if (duplicateLookupTimer) {
    clearTimeout(duplicateLookupTimer)
    duplicateLookupTimer = null
  }
}

function resetComposerForm(): void {
  preserveSubmitMessageOnReset = true
  selectedTemplateKey.value = ''
  clearDuplicateLookupTimer()
  resetDuplicateLookupState()
  form.type = ''
  form.related_id = ''
  form.raw_content = ''
  form.expected_behavior = ''
  form.actual_behavior = ''
  form.page_url = ''
  form.page_title = ''
  form.environment_context = ''
  hydrateContextDefaults(true)
}

async function loadDuplicateIssues(relatedId = normalizedRelatedId.value): Promise<void> {
  const requestId = ++duplicateLookupRequestId
  if (!relatedId || !isValidRelatedId(relatedId)) {
    resetDuplicateLookupState()
    return
  }
  duplicateLookupState.value = 'loading'
  duplicateLookupErrorMessage.value = ''
  try {
    const exactMatches = await fetchSubmittedIssues({ related_id: relatedId })
    if (requestId !== duplicateLookupRequestId) {
      return
    }
    if (exactMatches.length) {
      duplicateIssues.value = exactMatches
      duplicateMatchKind.value = 'exact'
      duplicateLookupState.value = 'idle'
      return
    }

    for (const keyword of buildRelatedKeywordCandidates(relatedId)) {
      const relatedMatches = await fetchSubmittedIssues({ keyword })
      if (requestId !== duplicateLookupRequestId) {
        return
      }
      if (relatedMatches.length) {
        duplicateIssues.value = relatedMatches
        duplicateMatchKind.value = 'related'
        duplicateLookupState.value = 'idle'
        return
      }
    }

    duplicateIssues.value = []
    duplicateLookupState.value = 'empty'
    duplicateMatchKind.value = 'exact'
  } catch (error) {
    if (requestId !== duplicateLookupRequestId) {
      return
    }
    duplicateIssues.value = []
    duplicateLookupState.value = 'error'
    duplicateMatchKind.value = 'exact'
    duplicateLookupErrorMessage.value = error instanceof Error ? error.message : '同主题检查失败，请稍后重试。'
  }
}

async function handleRelatedIdBlur(): Promise<void> {
  form.related_id = normalizeRelatedId(form.related_id)
  clearDuplicateLookupTimer()
  await loadDuplicateIssues()
}

async function applyRelatedExample(example: string): Promise<void> {
  suppressDuplicateLookupWatch = true
  form.related_id = normalizeRelatedId(example)
  clearDuplicateLookupTimer()
  await loadDuplicateIssues()
}

async function copyRelatedId(): Promise<void> {
  if (!lastSubmission.value) {
    return
  }

  try {
    await navigator.clipboard.writeText(lastSubmission.value.related_id)
    copyStateLabel.value = '已复制'
  } catch {
    copyStateLabel.value = '当前环境不支持复制'
  }
}

async function viewRelatedHistory(): Promise<void> {
  if (!lastSubmission.value) {
    return
  }

  filters.keyword = lastSubmission.value.related_id
  filters.type = 'all'
  await loadSubmittedIssues()
}

async function submitFeedback(): Promise<void> {
  submitting.value = true
  submitMessage.value = ''
  copyStateLabel.value = '复制关联标识'

  if (!form.type) {
    submitMessage.value = '请先选择反馈类型，再提交反馈。'
    submitting.value = false
    return
  }

  form.related_id = normalizeRelatedId(form.related_id)

  if (!isValidRelatedId(form.related_id)) {
    await nextTick()
    submitMessage.value = '关联标识请使用小写英文、数字和短横线，例如 github-submit-flow。'
    submitting.value = false
    return
  }

  const payload: FeedbackCreatePayload = {
    type: form.type,
    related_id: form.related_id,
    raw_content: form.raw_content,
    expected_behavior: form.expected_behavior || undefined,
    actual_behavior: form.actual_behavior || undefined,
    page_url: normalizePageUrl(form.page_url || '') || undefined,
    page_title: clampOptionalText(form.page_title, 200) || undefined,
    environment_context: clampOptionalText(form.environment_context, 500) || undefined,
  }
  try {
    const response = await apiPost<{ id: string; status: string; created_at: string }, FeedbackCreatePayload>(
      buildPublicApiPath('/feedback'),
      payload,
    )

    if (response.success) {
      submitMessage.value = `提交成功，反馈编号 ${response.data.id}`
      lastSubmission.value = {
        id: response.data.id,
        related_id: form.related_id,
        typeLabel: getTypeLabel(form.type),
        created_at: response.data.created_at,
      }
      resetComposerForm()
      await loadSubmittedIssues()
    } else {
      submitMessage.value = response.message || '提交失败，请检查输入后重试'
    }
  } catch {
    submitMessage.value = '提交失败，请检查网络后重试。'
  } finally {
    submitting.value = false
  }
}

watch(
  () => form.related_id,
  (value) => {
    if (value !== form.related_id) {
      return
    }
    if (preserveSubmitMessageOnReset) {
      preserveSubmitMessageOnReset = false
      return
    }
    submitMessage.value = ''
    const normalizedValue = value.trim().toLowerCase()
    clearDuplicateLookupTimer()
    if (suppressDuplicateLookupWatch) {
      suppressDuplicateLookupWatch = false
      return
    }
    if (!normalizedValue) {
      resetDuplicateLookupState()
      return
    }
    if (!isValidRelatedId(normalizedValue)) {
      resetDuplicateLookupState()
      return
    }
    duplicateLookupTimer = setTimeout(() => {
      duplicateLookupTimer = null
      void loadDuplicateIssues(normalizedValue)
    }, 250)
  },
)

watch(
  () => [form.type, form.raw_content, form.expected_behavior, form.actual_behavior],
  () => {
    if (suppressTemplateSelectionWatch || !selectedTemplateKey.value) {
      return
    }

    const template = quickTemplates.find((item) => item.key === selectedTemplateKey.value)
    if (!template) {
      selectedTemplateKey.value = ''
      return
    }

    const matchesSelectedTemplate =
      form.type === template.type &&
      form.raw_content === template.rawContent &&
      form.expected_behavior === template.expectedBehavior &&
      form.actual_behavior === template.actualBehavior

    if (!matchesSelectedTemplate) {
      selectedTemplateKey.value = ''
    }
  },
)

onMounted(async () => {
  hydrateContextDefaults()
  await loadSubmittedIssues()
})
</script>
