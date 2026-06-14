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
            <p>描述一个问题或建议。</p>
          </div>

          <form class="composer-form" @submit.prevent="submitFeedback">
            <section class="feedback-type-picker" aria-labelledby="feedback-type-title">
              <div class="feedback-type-picker__head">
                <div>
                  <span id="feedback-type-title">反馈类型</span>
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

            <div class="composer-row">
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
                    v-for="example in relatedExamples"
                    :key="example"
                    class="related-id-chip"
                    type="button"
                    @click="applyRelatedExample(example)"
                  >
                    {{ example }}
                  </button>
                </div>
              </div>

              <section class="duplicate-panel duplicate-panel--inline">
                <div class="studio-section-head studio-section-head--compact">
                  <div>
                    <span>Duplicate</span>
                    <h3>{{ duplicateIssues.length ? '发现同主题' : '查重' }}</h3>
                  </div>
                </div>
                <p v-if="duplicateIssues.length">已有 {{ duplicateIssues.length }} 条相关记录。</p>
                <p v-else>输入关联标识后显示同主题 Issue，提交前可快速判断是否已经有人反馈。</p>
                <ul v-if="duplicateIssues.length" class="duplicate-list duplicate-list--studio">
                  <li v-for="issue in duplicateIssues" :key="issue.issue_number">
                    <a :href="issue.issue_url" target="_blank" rel="noreferrer">#{{ issue.issue_number }} {{ issue.title }}</a>
                  </li>
                </ul>
              </section>
            </div>

            <label class="field field--full composer-main-field">
              <span>反馈内容</span>
              <textarea v-model="form.raw_content" class="textarea textarea--editor" rows="10" placeholder="描述触发场景、具体表现和影响范围"></textarea>
            </label>

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

            <div v-if="submitMessage" class="feedback-message field--full">{{ submitMessage }}</div>
            <div class="composer-actions">
              <span>{{ normalizedRelatedId || '等待关联标识' }}</span>
              <button class="button" type="submit">{{ submitting ? '提交中...' : '提交反馈' }}</button>
            </div>
          </form>
        </article>

          <aside class="intake-inspector">
          <section class="history-panel">
            <div class="studio-section-head">
              <div>
                <span>History</span>
                <h3>历史记录</h3>
              </div>
              <p>{{ historySectionHint }}</p>
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
            <div class="history-summary">
              <strong>{{ historySummaryTitle }}</strong>
              <span>{{ historySummaryHint }}</span>
            </div>
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

const relatedExamples = ['github-submit-flow', 'editor-copy-button', 'login-timeout', 'mobile-navbar']
const relatedIdPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

const submittedIssues = ref<SubmittedIssue[]>([])
const submittedIssueTotal = ref(0)
const issuesLoading = ref(false)
const duplicateIssues = ref<SubmittedIssue[]>([])
const submitting = ref(false)
const submitMessage = ref('')
const historyMessage = ref('')
let preserveSubmitMessageOnReset = false

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
})

const normalizedRelatedId = computed(() => form.related_id.trim())
const selectedTypeLabel = computed(() => (form.type ? getTypeLabel(form.type) : ''))
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

function selectFeedbackType(type: string): void {
  form.type = type
  submitMessage.value = ''
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

async function loadDuplicateIssues(): Promise<void> {
  if (!normalizedRelatedId.value || !isValidRelatedId(normalizedRelatedId.value)) {
    duplicateIssues.value = []
    return
  }
  const response = await apiGet<PaginatedResponse<SubmittedIssue>>(
    buildSubmittedIssueSearch({ related_id: normalizedRelatedId.value }),
  )
  duplicateIssues.value = response.success ? response.data.items : []
}

async function handleRelatedIdBlur(): Promise<void> {
  form.related_id = normalizeRelatedId(form.related_id)
  await loadDuplicateIssues()
}

async function applyRelatedExample(example: string): Promise<void> {
  form.related_id = normalizeRelatedId(example)
  await loadDuplicateIssues()
}

async function submitFeedback(): Promise<void> {
  submitting.value = true
  submitMessage.value = ''

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
  }
  try {
    const response = await apiPost<{ id: string; status: string; created_at: string }, FeedbackCreatePayload>(
      buildPublicApiPath('/feedback'),
      payload,
    )

    if (response.success) {
      submitMessage.value = `提交成功，反馈编号 ${response.data.id}`
      preserveSubmitMessageOnReset = true
      form.type = ''
      form.related_id = ''
      form.raw_content = ''
      form.expected_behavior = ''
      form.actual_behavior = ''
      duplicateIssues.value = []
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
  () => {
    if (preserveSubmitMessageOnReset) {
      preserveSubmitMessageOnReset = false
      return
    }
    submitMessage.value = ''
  },
)

onMounted(async () => {
  await loadSubmittedIssues()
})
</script>
