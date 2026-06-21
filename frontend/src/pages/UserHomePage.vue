<template>
  <AppShell title="Issue Intake" description="提交反馈，生成可追踪 Issue。">
    <section class="intake-studio">
      <header class="intake-hero">
        <div>
          <p class="eyebrow">Public Intake</p>
          <h2>提交反馈</h2>
          <p>选择类型、填写标识和内容即可提交。</p>
        </div>
        <div class="intake-hero__metrics">
          <span>已提交 Issue</span>
          <strong>{{ submittedIssueTotal }}</strong>
        </div>
      </header>

      <section class="intake-grid">
        <article class="feedback-composer">
          <form class="composer-form" @submit.prevent="submitFeedback">
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

            <label class="field field--full">
              <span>关联标识</span>
              <input
                v-model="form.related_id"
                class="input"
                placeholder="editor-copy-button"
                @blur="handleRelatedIdBlur"
              />
              <small class="field-helper">
                用小写英文、数字和短横线，例如 github-submit-flow；空格和下划线会自动转成短横线。
              </small>
            </label>

            <div v-if="showDuplicateInfo" class="duplicate-hint" :class="`duplicate-hint--${duplicateStateTone}`">
              <template v-if="duplicateIssues.length">
                <strong>{{ duplicatePanelTitle }}</strong>
                <p>{{ duplicateSummary }} {{ duplicateActionTitle }}</p>
                <p class="duplicate-hint__action">{{ duplicateActionHint }}</p>
                <ul class="duplicate-hint__list">
                  <li v-for="issue in duplicateIssues" :key="issue.issue_number">
                    <a :href="issue.issue_url" target="_blank" rel="noopener">#{{ issue.issue_number }}</a>
                    {{ issue.title }}
                  </li>
                </ul>
              </template>
              <template v-else>
                <strong>{{ duplicateStatusLabel }}</strong>
                <p>{{ duplicateActionTitle }}</p>
                <p v-if="duplicateLookupState === 'error'" class="duplicate-hint__error">{{ duplicateLookupErrorMessage }}</p>
                <p class="duplicate-hint__action">{{ duplicateActionHint }}</p>
              </template>
            </div>

            <label class="field field--full">
              <span>反馈内容</span>
              <textarea
                v-model="form.raw_content"
                class="textarea"
                rows="6"
                placeholder="描述触发场景、具体表现和影响范围"
              ></textarea>
            </label>

            <div v-if="submitMessage" class="feedback-message field--full">{{ submitMessage }}</div>

            <div v-if="lastSubmission" class="submission-summary">
              <strong>最近一次提交</strong>
              <p>{{ lastSubmission.typeLabel }} / {{ lastSubmission.related_id }}</p>
              <small>ID {{ lastSubmission.id }} · {{ lastSubmission.created_at }}</small>
              <div class="submission-summary__actions">
                <button type="button" class="button button--quiet" @click="copyRelatedId">{{ copyStateLabel }}</button>
                <button type="button" class="button button--quiet" @click="viewRelatedHistory">查看同标识历史</button>
              </div>
            </div>

            <div class="composer-actions">
              <span>
                {{ submissionReadinessText }}
                <small class="composer-actions__note">同一 IP 每天最多提交 5 次反馈。</small>
              </span>
              <button class="button" type="submit">{{ submitting ? '提交中...' : '提交反馈' }}</button>
            </div>
          </form>
        </article>

        <IntakeInspector
          :type="form.type"
          :type-label="selectedTypeLabel"
          :has-valid-related-id="hasValidRelatedId"
          :normalized-related-id="normalizedRelatedId"
          :raw-content="form.raw_content.trim()"
          :has-context="false"
          :context-summary="''"
          :issues="submittedIssues"
          :loading="issuesLoading"
          :history-message="historyMessage"
          :history-summary-title="historySummaryTitle"
          :history-summary-hint="historySummaryHint"
          :empty-title="historyEmptyTitle"
          :empty-hint="historyEmptyHint"
          :keyword="filters.keyword"
          :type-filter="filters.type"
          @search="
            (k: string, t: string) => {
              filters.keyword = k
              filters.type = t as any
              loadSubmittedIssues()
            }
          "
        />
      </section>
    </section>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import AppShell from '../components/layout/AppShell.vue'
import IntakeInspector from '../components/common/IntakeInspector.vue'
import { getTypeLabel } from '../components/common/IntakeInspector.utils'
import {
  apiGet,
  apiPost,
  buildPublicApiPath,
  buildSubmittedIssueSearch,
  type FeedbackCreatePayload,
  type PaginatedResponse,
  type SubmittedIssue,
} from '../services/api'

const feedbackTypeOptions = [
  { value: 'bug', label: '缺陷', description: '功能异常、报错、结果不符合预期' },
  { value: 'feature', label: '新功能', description: '希望新增的能力或完整流程' },
  { value: 'enhancement', label: '优化', description: '体验、性能、文案或交互改进' },
  { value: 'question', label: '问题', description: '需要确认规则、边界或使用方式' },
]

const relatedIdPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

const submittedIssues = ref<SubmittedIssue[]>([])
const submittedIssueTotal = ref(0)
const issuesLoading = ref(false)
const duplicateIssues = ref<SubmittedIssue[]>([])
const duplicateLookupState = ref<'idle' | 'loading' | 'empty' | 'error'>('idle')
const duplicateMatchKind = ref<'exact' | 'related'>('exact')
const duplicateLookupErrorMessage = ref('')
const submitting = ref(false)
const submitMessage = ref('')
const historyMessage = ref('')
const lastSubmission = ref<{ id: string; related_id: string; typeLabel: string; created_at: string } | null>(null)
const copyStateLabel = ref('复制关联标识')
let duplicateLookupTimer: ReturnType<typeof setTimeout> | null = null
let duplicateLookupRequestId = 0
let previousRelatedId = ''
let skipNextDuplicateLookup = false

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
})

const normalizedRelatedId = computed(() => form.related_id.trim())
const selectedTypeLabel = computed(() => (form.type ? getTypeLabel(form.type) : ''))
const hasValidRelatedId = computed(() => isValidRelatedId(normalizedRelatedId.value))
const showDuplicateInfo = computed(
  () => normalizedRelatedId.value || duplicateLookupState.value === 'loading',
)

const hasHistoryFilters = computed(() => Boolean(filters.keyword.trim()) || filters.type !== 'all')
const historySummaryTitle = computed(() => {
  if (issuesLoading.value) return '正在刷新历史记录'
  if (hasHistoryFilters.value) return `当前结果 ${submittedIssues.value.length} 条`
  return `最近记录 ${submittedIssues.value.length} 条`
})
const historySummaryHint = computed(() => {
  if (hasHistoryFilters.value) {
    const parts = []
    if (filters.keyword.trim()) parts.push(`关键词 ${filters.keyword.trim()}`)
    if (filters.type !== 'all') parts.push(`类型 ${getTypeLabel(filters.type)}`)
    return parts.length ? `已按 ${parts.join(' / ')} 筛选` : '已应用筛选'
  }
  return `累计已提交 ${submittedIssueTotal.value} 条 Issue`
})
const historyEmptyTitle = computed(() => (hasHistoryFilters.value ? '没有匹配结果' : '暂无历史记录'))
const historyEmptyHint = computed(() => {
  if (hasHistoryFilters.value) return '调整关键词或类型后重新搜索，或者查看全部历史记录。'
  return '搜索结果会在这里展示，便于确认同类问题是否已经进入 GitHub。'
})

const duplicatePanelTitle = computed(() => (duplicateMatchKind.value === 'exact' ? '发现同标识' : '发现相近主题'))
const duplicateSummary = computed(() => {
  const matchLabel = duplicateMatchKind.value === 'exact' ? '同标识' : '相近主题'
  return `已有 ${duplicateIssues.value.length} 条${matchLabel}记录。`
})
const duplicateStateTone = computed(() => {
  if (duplicateIssues.value.length) return duplicateMatchKind.value === 'exact' ? 'match' : 'related'
  if (!normalizedRelatedId.value) return 'idle'
  if (!hasValidRelatedId.value) return 'warning'
  if (duplicateLookupState.value === 'loading') return 'loading'
  if (duplicateLookupState.value === 'error') return 'error'
  if (duplicateLookupState.value === 'empty') return 'clear'
  return 'idle'
})
const duplicateStatusLabel = computed(() => {
  if (duplicateIssues.value.length) return duplicateMatchKind.value === 'exact' ? '已命中' : '有相近项'
  if (!normalizedRelatedId.value) return '待输入'
  if (!hasValidRelatedId.value) return '需修正'
  if (duplicateLookupState.value === 'loading') return '检查中'
  if (duplicateLookupState.value === 'error') return '检查失败'
  if (duplicateLookupState.value === 'empty') return '可继续'
  return '待输入'
})
const duplicateActionTitle = computed(() => {
  if (duplicateIssues.value.length) {
    return duplicateMatchKind.value === 'exact'
      ? '先看已有记录，再决定是否补充新证据。'
      : '先确认是否属于同一主题，再决定是否继续提交。'
  }
  if (!normalizedRelatedId.value) return '先填关联标识，系统会自动对照已有 Issue。'
  if (!hasValidRelatedId.value) return '先把标识格式修正为小写英文、数字和短横线。'
  if (duplicateLookupState.value === 'loading') return '系统正在比对同主题记录。'
  if (duplicateLookupState.value === 'error') return '查重暂时不可用，建议稍后重试一次。'
  if (duplicateLookupState.value === 'empty') return '当前没有找到同主题记录。'
  return '先填关联标识，系统会自动对照已有 Issue。'
})
const duplicateActionHint = computed(() => {
  if (duplicateIssues.value.length) {
    return duplicateMatchKind.value === 'exact'
      ? '如果只是补充复现路径、截图或影响范围，优先复用现有主题，避免重复提单。'
      : '如果标题和场景高度接近，优先查看已有 Issue，确认能否合并到同一主题。'
  }
  if (!normalizedRelatedId.value) return '建议按页面、流程或组件命名，例如 github-submit-flow。'
  if (!hasValidRelatedId.value) return '格式正确后会自动开始查重，无需额外点击。'
  if (duplicateLookupState.value === 'loading') return '检查完成前可以先补正文，结果会自动更新在这里。'
  if (duplicateLookupState.value === 'error') return '如果你确认问题紧急，可以先完成正文填写，稍后再重新检查一次。'
  if (duplicateLookupState.value === 'empty') return '可以继续填写正文并提交，后台会按主题继续聚合。'
  return '建议按页面、流程或组件命名，例如 github-submit-flow。'
})
const submissionReadinessText = computed(() => {
  if (!form.type) return '先选择反馈类型'
  if (!normalizedRelatedId.value) return '再输入关联标识'
  if (!hasValidRelatedId.value) return '关联标识格式需为小写英文、数字和短横线'
  if (!form.raw_content.trim()) return '最后补一段核心描述即可提交'
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

function selectFeedbackType(value: string) {
  form.type = value
}

function handleRelatedIdBlur() {
  const normalized = normalizeRelatedId(form.related_id)
  if (normalized !== form.related_id) {
    form.related_id = normalized
  }
}

function clearScheduledDuplicateLookup() {
  if (!duplicateLookupTimer) return
  clearTimeout(duplicateLookupTimer)
  duplicateLookupTimer = null
}

onMounted(() => {
  loadSubmittedIssues()
})

onBeforeUnmount(() => {
  clearScheduledDuplicateLookup()
  duplicateLookupRequestId += 1
})

async function loadSubmittedIssues() {
  issuesLoading.value = true
  historyMessage.value = ''
  try {
    const url =
      filters.keyword.trim() || filters.type !== 'all'
        ? buildSubmittedIssueSearch({
            keyword: filters.keyword.trim() || undefined,
            type: filters.type !== 'all' ? filters.type : undefined,
          })
        : buildPublicApiPath('/issues/submitted')
    const response = (await apiGet(url)) as { success: boolean; data?: PaginatedResponse<SubmittedIssue>; message?: string }
    if (response.success && response.data) {
      submittedIssues.value = response.data.items
      submittedIssueTotal.value = response.data.total
    } else {
      historyMessage.value = response.message || '已提交 Issue 加载失败，请稍后重试。'
    }
  } catch {
    historyMessage.value = '已提交 Issue 加载失败，请稍后重试。'
  } finally {
    issuesLoading.value = false
  }
}

function lookupDuplicates(rawId: string) {
  const normalized = normalizeRelatedId(rawId)
  if (!normalized || !isValidRelatedId(normalized)) {
    duplicateIssues.value = []
    duplicateLookupState.value = 'idle'
    return
  }

  duplicateLookupState.value = 'loading'
  const requestId = ++duplicateLookupRequestId

  const exactPromise = apiGet(buildSubmittedIssueSearch({ related_id: normalized }))
  if (!exactPromise || typeof exactPromise.then !== 'function') {
    duplicateLookupState.value = 'idle'
    return
  }
  exactPromise
    .then((response: any) => {
      if (requestId !== duplicateLookupRequestId) return
      if (!response?.success) {
        duplicateLookupErrorMessage.value = response?.message || '同主题检查失败，请稍后重试。'
        duplicateLookupState.value = 'error'
        duplicateIssues.value = []
        return
      }
      if (response.data?.items?.length) {
        duplicateIssues.value = response.data.items
        duplicateMatchKind.value = 'exact'
        duplicateLookupState.value = 'idle'
      } else {
        return apiGet(buildSubmittedIssueSearch({ keyword: normalized.replace(/-/g, ' ').split(' ')[0] }))
      }
    })
    .then((response: any) => {
      if (!response || requestId !== duplicateLookupRequestId) return
      if (!response?.success) {
        duplicateLookupState.value = 'empty'
        duplicateIssues.value = []
        return
      }
      if (response.data?.items?.length) {
        duplicateIssues.value = response.data.items
        duplicateMatchKind.value = 'related'
        duplicateLookupState.value = 'idle'
      } else if (duplicateLookupState.value === 'loading') {
        duplicateIssues.value = []
        duplicateLookupState.value = 'empty'
      }
    })
    .catch(() => {
      if (requestId !== duplicateLookupRequestId) return
      duplicateIssues.value = []
      duplicateLookupState.value = 'error'
      duplicateLookupErrorMessage.value = '同主题检查失败，请稍后重试。'
    })
}

function scheduleDuplicateLookup(rawId: string) {
  if (skipNextDuplicateLookup) {
    skipNextDuplicateLookup = false
    lookupDuplicates(rawId)
    return
  }

  clearScheduledDuplicateLookup()
  duplicateLookupTimer = setTimeout(() => {
    duplicateLookupTimer = null
    lookupDuplicates(rawId)
  }, 200)
}

async function submitFeedback() {
  if (!form.type) {
    submitMessage.value = '请先选择反馈类型'
    return
  }
  if (!normalizedRelatedId.value || !hasValidRelatedId.value) {
    submitMessage.value = '关联标识请使用小写英文、数字和短横线'
    return
  }
  if (!form.raw_content.trim()) {
    submitMessage.value = '请填写反馈内容'
    return
  }

  submitting.value = true
  submitMessage.value = ''
  try {
    const response = (await apiPost(buildPublicApiPath('/feedback'), {
      ...form,
      related_id: normalizedRelatedId.value,
      page_url: typeof window !== 'undefined' ? window.location.href.split('#')[0].split('?')[0] : '',
    })) as { success: boolean; data?: any; message?: string }
    if (response.success && response.data) {
      const typeLabel = getTypeLabel(form.type)
      submitMessage.value = `提交成功，反馈编号 ${response.data.id}`
      lastSubmission.value = {
        id: response.data.id,
        related_id: normalizedRelatedId.value,
        typeLabel,
        created_at: response.data.created_at || '',
      }
      form.type = ''
      form.related_id = ''
      form.raw_content = ''
      duplicateIssues.value = []
      duplicateLookupState.value = 'idle'
      duplicateMatchKind.value = 'exact'
      previousRelatedId = ''
      clearScheduledDuplicateLookup()
      duplicateLookupRequestId += 1
      copyStateLabel.value = '复制关联标识'
      await loadSubmittedIssues()
    } else {
      submitMessage.value = response.message || '提交失败，请稍后重试'
    }
  } catch {
    submitMessage.value = '提交失败，请检查网络后重试'
  } finally {
    submitting.value = false
  }
}

function copyRelatedId() {
  if (!lastSubmission.value) return
  navigator.clipboard.writeText(lastSubmission.value.related_id).then(() => {
    copyStateLabel.value = '已复制'
    setTimeout(() => {
      copyStateLabel.value = '复制关联标识'
    }, 2000)
  })
}

function viewRelatedHistory() {
  if (!lastSubmission.value) return
  filters.keyword = lastSubmission.value.related_id
  filters.type = 'all'
  loadSubmittedIssues()
}

watch(
  () => form.related_id,
  (value) => {
    const normalized = normalizeRelatedId(value)
    if (normalized !== value && !skipNextDuplicateLookup) {
      skipNextDuplicateLookup = true
      form.related_id = normalized
    }
    if (normalized === previousRelatedId) return
    previousRelatedId = normalized
    scheduleDuplicateLookup(normalized)
  },
)
</script>
