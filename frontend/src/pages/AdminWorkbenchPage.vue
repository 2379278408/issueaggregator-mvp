<template>
  <AppShell
    title="Issue Triage Studio"
    description="整理反馈，生成 GitHub Issue 草稿。"
  >
    <section v-if="!isAdminUnlocked" class="admin-auth-screen">
      <form class="admin-auth-card" @submit.prevent="unlockAdmin">
        <p class="eyebrow">Restricted Area</p>
        <h2>输入管理凭据</h2>
        <p>输入管理 token 后加载队列和草稿。</p>
        <label class="field field--full">
          <span>管理 token</span>
          <input v-model="adminTokenInput" class="input" type="password" autocomplete="current-password" placeholder="X-Admin-Token" />
        </label>
        <div v-if="adminAuthMessage" class="feedback-message feedback-message--error">{{ adminAuthMessage }}</div>
        <button class="button" type="submit">进入管理页</button>
      </form>
    </section>

    <section v-else class="triage-studio">
      <header class="triage-studio__header">
        <div>
          <p class="eyebrow">Private Studio</p>
          <h2>整理反馈，生成 Issue</h2>
          <p>选择信号、确认主题、编辑草稿。</p>
        </div>
        <div class="triage-studio__stats" aria-label="反馈状态统计">
          <button class="triage-tab" :class="{ 'is-active': queueStatus === 'pending' }" type="button" @click="switchQueue('pending')">
            <span>待整理</span>
            <strong>{{ statusCounts.pending }}</strong>
          </button>
          <button class="triage-tab" :class="{ 'is-active': queueStatus === 'grouped' }" type="button" @click="switchQueue('grouped')">
            <span>草稿中</span>
            <strong>{{ statusCounts.grouped }}</strong>
          </button>
          <button class="triage-tab" :class="{ 'is-active': queueStatus === 'submitted' }" type="button" @click="switchQueue('submitted')">
            <span>已发布</span>
            <strong>{{ statusCounts.submitted }}</strong>
          </button>
        </div>
      </header>

      <section class="triage-grid">
        <article id="queue-panel" class="signal-stream">
          <header class="studio-section-head">
            <div>
              <span>Signal Stream</span>
              <h3>{{ queueHeading }}</h3>
            </div>
            <p>{{ queueDescription }}</p>
          </header>

          <div class="signal-list">
            <section v-for="section in queueSections" :key="section.label" class="signal-group">
              <div class="signal-group__label">
                <strong>{{ section.label }}</strong>
                <span>{{ section.items.length }}</span>
              </div>
              <button
                v-for="item in section.items"
                :key="item.id"
                class="signal-card"
                :class="{ 'is-active': isQueueItemActive(item) }"
                type="button"
                @click="handleQueueItemClick(item)"
              >
                <div class="signal-card__meta">
                  <span>{{ getTypeLabel(item.type) }}</span>
                  <span>{{ describeQueueItemTime(item) }}</span>
                </div>
                <div class="signal-card__title">
                  <strong>{{ item.related_id }}</strong>
                  <input
                    v-if="queueStatus === 'pending'"
                    :checked="selectedIds.includes(item.id)"
                    type="checkbox"
                    aria-label="选择反馈"
                    @click.stop
                    @change="toggleSelection(item.id)"
                  />
                </div>
                <p>{{ excerpt(item.raw_content, 92) }}</p>
              </button>
            </section>
            <div v-if="!queueItems.length && !loading" class="empty-state">暂无内容。</div>
            <div v-if="loading" class="empty-state">正在载入...</div>
          </div>
        </article>

        <article id="review-panel" class="topic-canvas">
          <header class="studio-section-head">
            <div>
              <span>Topic Canvas</span>
              <h3>{{ reviewHeadline }}</h3>
            </div>
            <p>{{ reviewDescription }}</p>
          </header>

          <section class="topic-summary" :class="reviewDecisionToneClass">
            <span>判断</span>
            <strong>{{ reviewDecisionTitle }}</strong>
            <p>{{ reviewDecisionDescription }}</p>
          </section>

          <div class="topic-facts">
            <article>
              <span>主题</span>
              <strong>{{ batchSummary.primaryRelatedId || activeReferenceRelatedId || '待选择' }}</strong>
            </article>
            <article>
              <span>信号</span>
              <strong>{{ reviewItems.length }}</strong>
            </article>
            <article>
              <span>缺失</span>
              <strong>{{ reviewMissingCount }}</strong>
            </article>
          </div>

          <div class="evidence-list">
            <article v-for="item in reviewItems" :key="item.id" class="evidence-card">
              <div class="evidence-card__meta">
                <span>{{ getTypeLabel(item.type) }}</span>
                <strong>{{ item.related_id }}</strong>
                <span>{{ getMissingFieldCount(item) ? `缺失 ${getMissingFieldCount(item)} 项` : '信息完整' }}</span>
              </div>
              <p>{{ item.raw_content }}</p>
              <dl>
                <div>
                  <dt>期望</dt>
                  <dd>{{ item.expected_behavior || '待补充' }}</dd>
                </div>
                <div>
                  <dt>实际</dt>
                  <dd>{{ item.actual_behavior || '待补充' }}</dd>
                </div>
              </dl>
            </article>
            <div v-if="!reviewItems.length" class="empty-state">选择反馈后生成主题画布。</div>
          </div>

          <div v-if="batchMessage" class="feedback-message">{{ batchMessage }}</div>
          <div class="studio-actions">
            <button class="button button--secondary" type="button" :disabled="queueStatus !== 'pending' || creatingBatch" @click="createBatch">
              {{ creatingBatch ? '创建中...' : batchSummary.isMixed ? '确认建批' : '创建批次' }}
            </button>
            <button class="button" type="button" :disabled="!activeBatchId || integratingDraft" @click="integrateDraft">
              {{ integratingDraft ? '生成中...' : '生成草稿' }}
            </button>
          </div>
        </article>

        <article id="draft-panel" class="issue-editor">
          <header class="studio-section-head">
            <div>
              <span>Issue Draft</span>
              <h3>{{ draftStatusLabel }}</h3>
            </div>
            <p>{{ draftStatusDescription }}</p>
          </header>

          <div class="issue-editor__meta">
            <span>{{ draftRelatedIdSummary }}</span>
            <span>{{ activeBatchId || '待建批' }}</span>
            <span>{{ draftUpdatedAtLabel }}</span>
          </div>

          <label class="field field--full issue-title-field">
            <span>Issue 标题</span>
            <input v-model="draftForm.title" class="input" :readonly="!currentDraftId" />
          </label>
          <label class="field field--full issue-body-field">
            <span>Issue 正文</span>
            <textarea v-model="draftForm.body_markdown" class="textarea textarea--editor" rows="18" :readonly="!currentDraftId"></textarea>
          </label>

          <div v-if="draftMessage" class="feedback-message draft-message">{{ draftMessage }}</div>
          <div v-if="submissionResult" class="warning-box submission-card submission-card--result">
            <strong>GitHub Issue #{{ submissionResult.issue_number }}</strong>
            <p>
              已提交到
              <a :href="submissionResult.issue_url" target="_blank" rel="noreferrer">GitHub</a>
              ，时间 {{ submissionResult.submitted_at }}
            </p>
          </div>

          <div class="studio-actions issue-actions">
            <button class="button button--secondary" type="button" :disabled="!activeBatchId || integratingDraft" @click="integrateDraft">
              {{ integratingDraft ? '生成中...' : '生成草稿' }}
            </button>
            <button class="button button--secondary" type="button" :disabled="!currentDraftId || savingDraft" @click="saveDraft">
              {{ savingDraft ? '保存中...' : '保存草稿' }}
            </button>
            <button class="button" type="button" :disabled="!currentDraftId || submittingDraft" @click="submitDraftToGithub">
              {{ submittingDraft ? '提交中...' : '提交 GitHub' }}
            </button>
          </div>
        </article>
      </section>
    </section>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import AppShell from '../components/layout/AppShell.vue'
import {
  apiGet,
  apiPost,
  apiPut,
  buildAdminApiPath,
  hasAdminToken,
  setAdminToken,
  type DraftBatchCreatePayload,
  type DraftBatchCreateResponse,
  type DraftIntegrateResponse,
  type DraftRecord,
  type DraftSubmitResponse,
  type DraftUpdatePayload,
  type FeedbackItem,
  type PaginatedResponse,
} from '../services/api'

type QueueStatus = 'pending' | 'grouped' | 'submitted'
type AdminSection = 'queue' | 'review' | 'draft'

const typeLabelMap: Record<string, string> = {
  bug: '缺陷',
  feature: '新功能',
  enhancement: '优化',
  question: '问题',
}

const statusLabelMap: Record<string, string> = {
  pending: '待处理',
  grouped: '已分组',
  submitted: '已提交',
}

const pendingItems = ref<FeedbackItem[]>([])
const groupedItems = ref<FeedbackItem[]>([])
const submittedItems = ref<FeedbackItem[]>([])
const selectedIds = ref<string[]>([])
const queueStatus = ref<QueueStatus>('pending')
const activeAdminSection = ref<AdminSection>('queue')
const activeReferenceId = ref('')
const loading = ref(false)
const creatingBatch = ref(false)
const integratingDraft = ref(false)
const savingDraft = ref(false)
const submittingDraft = ref(false)
const batchMessage = ref('')
const draftMessage = ref('')
const activeBatchId = ref('')
const currentDraftId = ref('')
const submissionResult = ref<DraftSubmitResponse | null>(null)
const currentDraftRecord = ref<DraftRecord | null>(null)
const isAdminUnlocked = ref(hasAdminToken())
const adminTokenInput = ref('')
const adminAuthMessage = ref('')

const draftForm = reactive<DraftUpdatePayload>({
  title: '[草稿] 请选择反馈后生成标题',
  body_markdown: '摘要\n\n关联标识\n\n用户信号数量',
})

const statusCounts = computed(() => ({
  pending: pendingItems.value.length,
  grouped: groupedItems.value.length,
  submitted: submittedItems.value.length,
}))

const selectedItems = computed(() => pendingItems.value.filter((item) => selectedIds.value.includes(item.id)))

const queueItems = computed(() => {
  if (queueStatus.value === 'grouped') {
    return groupedItems.value
  }
  if (queueStatus.value === 'submitted') {
    return submittedItems.value
  }
  return pendingItems.value
})

const queueSections = computed(() => {
  const sections = [
    { label: '今天', items: [] as FeedbackItem[] },
    { label: '最近 7 天', items: [] as FeedbackItem[] },
    { label: '更早', items: [] as FeedbackItem[] },
    { label: '未标注时间', items: [] as FeedbackItem[] },
  ]

  queueItems.value.forEach((item) => {
    const bucket = getQueueTimeBucket(item)
    const target = sections.find((section) => section.label === bucket)
    target?.items.push(item)
  })

  return sections.filter((section) => section.items.length > 0)
})

const activeReferenceItem = computed(() => queueItems.value.find((item) => item.id === activeReferenceId.value) || null)

const reviewItems = computed(() => {
  if (queueStatus.value === 'pending') {
    return selectedItems.value
  }
  return activeReferenceItem.value ? [activeReferenceItem.value] : []
})

const batchSummary = computed(() => {
  const relatedIds = [...new Set(selectedItems.value.map((item) => item.related_id))]
  return {
    primaryRelatedId: relatedIds.length === 1 ? relatedIds[0] : null,
    itemCount: selectedItems.value.length,
    isMixed: relatedIds.length > 1,
    relatedIdCount: relatedIds.length,
  }
})

const activeReferenceRelatedId = computed(() => activeReferenceItem.value?.related_id || '')

const reviewMissingCount = computed(() => reviewItems.value.reduce((total, item) => total + getMissingFieldCount(item), 0))

const reviewCanCreateBatch = computed(() => {
  if (queueStatus.value !== 'pending') {
    return Boolean(activeReferenceItem.value)
  }
  return selectedItems.value.length > 0
})

const reviewDecisionTitle = computed(() => {
  if (queueStatus.value !== 'pending') {
    return activeReferenceItem.value ? '当前记录可作为回看参考' : '等待选择参考记录'
  }
  if (!selectedItems.value.length) {
    return '先选择要进入本轮判断的反馈'
  }
  if (batchSummary.value.isMixed) {
    return '当前反馈涉及多个关联标识，建议拆分主题'
  }
  if (reviewMissingCount.value > 0) {
    return '当前主题集中，但存在待补充信息'
  }
  return '当前反馈可以直接进入建批'
})

const reviewDecisionDescription = computed(() => {
  if (queueStatus.value !== 'pending') {
    return activeReferenceItem.value
      ? '这条记录已经进入后续流程，可以用来回看聚合结果与草稿上下文。'
      : '从左侧已分组或已提交队列选择一条记录，这里会显示决策判断。'
  }
  if (!selectedItems.value.length) {
    return '从左侧收件箱中勾选反馈，系统会给出是否适合建批、是否建议拆分以及缺失信息提示。'
  }
  if (batchSummary.value.isMixed) {
    return `当前共包含 ${batchSummary.value.relatedIdCount} 个关联标识，拆成多个批次更利于后续草稿聚合和提交。`
  }
  if (reviewMissingCount.value > 0) {
    return `当前主题已经集中，但还有 ${reviewMissingCount.value} 处关键信息待补充，草稿阶段需要人工修订。`
  }
  return '关联标识一致，关键信息完整度也足够，可以直接创建批次并生成草稿。'
})

const reviewDecisionToneClass = computed(() => {
  if (queueStatus.value !== 'pending') {
    return 'is-neutral'
  }
  if (!selectedItems.value.length) {
    return 'is-idle'
  }
  if (batchSummary.value.isMixed) {
    return 'is-warning'
  }
  if (reviewMissingCount.value > 0) {
    return 'is-caution'
  }
  return 'is-ready'
})

const draftPreviewTitle = computed(() => {
  if (currentDraftId.value) {
    return draftForm.title
  }
  if (!selectedItems.value.length) {
    return '[草稿] 请选择反馈后生成标题'
  }
  if (batchSummary.value.primaryRelatedId) {
    return `[草稿] ${batchSummary.value.primaryRelatedId}`
  }
  return '[草稿] 混合关联标识批次'
})

const draftStatusLabel = computed(() => {
  if (submissionResult.value) {
    return '已提交'
  }
  if (currentDraftRecord.value?.status === 'draft_ready' || currentDraftId.value) {
    return '待提交'
  }
  if (activeBatchId.value) {
    return '待生成'
  }
  return '未开始'
})

const draftStatusDescription = computed(() => {
  if (submissionResult.value) {
    return `GitHub Issue #${submissionResult.value.issue_number} 已创建，可继续回看本次处理记录。`
  }
  if (currentDraftId.value) {
    return '草稿已经生成。这里保留当前批次的唯一编辑上下文，适合人工修订后直接提交。'
  }
  if (activeBatchId.value) {
    return '批次已经创建，下一步生成结构化草稿。'
  }
  return '先从左侧队列选择反馈并创建批次，这里会进入草稿编辑状态。'
})

const draftRelatedIdSummary = computed(() => {
  if (submissionResult.value?.related_id) {
    return submissionResult.value.related_id
  }
  if (currentDraftRecord.value?.related_id_summary) {
    return currentDraftRecord.value.related_id_summary
  }
  return batchSummary.value.primaryRelatedId || activeReferenceRelatedId.value || '待确认'
})

const draftUpdatedAtLabel = computed(() => {
  if (submissionResult.value?.submitted_at) {
    return submissionResult.value.submitted_at
  }
  if (currentDraftRecord.value?.updated_at) {
    return currentDraftRecord.value.updated_at
  }
  return '尚未生成'
})

const queueHeading = computed(() => statusLabelMap[queueStatus.value])

const queueDescription = computed(() => {
  if (queueStatus.value === 'grouped') {
    return '查看已进入批次、等待继续处理的反馈。'
  }
  if (queueStatus.value === 'submitted') {
    return '查看已经完成提交的反馈记录。'
  }
  return '勾选同一主题的反馈，准备创建批次。'
})

const reviewHeadline = computed(() => {
  if (queueStatus.value === 'pending') {
    return selectedItems.value.length ? '当前选中反馈' : '等待选择反馈'
  }
  return activeReferenceItem.value ? '当前参考记录' : '等待选择参考项'
})

const reviewDescription = computed(() => {
  if (queueStatus.value === 'pending') {
    return selectedItems.value.length
      ? '确认这些反馈是否属于同一主题，再创建批次。'
      : '从左侧队列中选择待处理反馈，这里会显示原始内容和补充信息。'
  }
  return activeReferenceItem.value
    ? '这里展示已处理记录的上下文，便于回看聚合结果。'
    : '从左侧已分组或已提交队列选择一条记录，这里会显示详情。'
})

const workflowSteps = computed(() => [
  { index: '1', label: '选中反馈', state: selectedItems.value.length ? 'is-done' : 'is-current' },
  { index: '2', label: '创建批次', state: activeBatchId.value ? 'is-done' : 'is-idle' },
  { index: '3', label: '生成草稿', state: currentDraftId.value ? 'is-done' : 'is-idle' },
  { index: '4', label: '提交 GitHub', state: submissionResult.value ? 'is-done' : 'is-idle' },
])

const activeAdminSectionLabel = computed(() => {
  if (activeAdminSection.value === 'review') {
    return '聚合审阅'
  }
  if (activeAdminSection.value === 'draft') {
    return '草稿与提交'
  }
  return '反馈队列'
})

let sectionObserver: IntersectionObserver | null = null

function getTypeLabel(type: string): string {
  return typeLabelMap[type] || type
}

function getStatusLabel(status: string): string {
  return statusLabelMap[status] || status
}

function excerpt(text: string, maxLength = 96): string {
  if (text.length <= maxLength) {
    return text
  }
  return `${text.slice(0, maxLength)}...`
}

function getMissingFieldCount(item: FeedbackItem): number {
  let count = 0
  if (!item.expected_behavior) {
    count += 1
  }
  if (!item.actual_behavior) {
    count += 1
  }
  return count
}

function formatTimestamp(value: string | null | undefined): string {
  return value || '刚刚更新'
}

function toComparableDate(value: string | null | undefined): Date | null {
  if (!value) {
    return null
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return parsed
}

function getQueueTimeBucket(item: FeedbackItem): '今天' | '最近 7 天' | '更早' | '未标注时间' {
  const value = item.submitted_at || item.created_at
  const timestamp = toComparableDate(value)
  if (!timestamp) {
    return '未标注时间'
  }

  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const sevenDaysAgo = new Date(startOfToday)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 6)

  if (timestamp >= startOfToday) {
    return '今天'
  }

  if (timestamp >= sevenDaysAgo) {
    return '最近 7 天'
  }

  return '更早'
}

function describeQueueItemTime(item: FeedbackItem): string {
  const value = item.submitted_at || item.created_at
  const timestamp = toComparableDate(value)
  if (!timestamp) {
    return formatTimestamp(value)
  }

  const now = new Date()
  const diffHours = Math.max(0, Math.floor((now.getTime() - timestamp.getTime()) / (1000 * 60 * 60)))
  if (diffHours < 1) {
    return '1 小时内'
  }

  if (diffHours < 24) {
    return `${diffHours} 小时前`
  }

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) {
    return `${diffDays} 天前`
  }

  return timestamp.toLocaleDateString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
  })
}

function switchQueue(status: QueueStatus): void {
  queueStatus.value = status
  activeAdminSection.value = 'queue'
  activeReferenceId.value = ''
  batchMessage.value = ''
  draftMessage.value = ''
  resetProcessingContext()
  if (status !== 'pending') {
    selectedIds.value = []
  }
}

function setActiveAdminSection(section: AdminSection): void {
  activeAdminSection.value = section
}

async function focusAdminSection(section: AdminSection): Promise<void> {
  activeAdminSection.value = section

  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return
  }

  await nextTick()

  const elementId = section === 'queue' ? 'queue-panel' : section === 'review' ? 'review-panel' : 'draft-panel'
  const element = document.getElementById(elementId)
  if (!element) {
    return
  }

  element.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

function isQueueItemActive(item: FeedbackItem): boolean {
  if (queueStatus.value === 'pending') {
    return selectedIds.value.includes(item.id)
  }
  return activeReferenceId.value === item.id
}

function handleQueueItemClick(item: FeedbackItem): void {
  batchMessage.value = ''
  draftMessage.value = ''
  if (queueStatus.value === 'pending') {
    toggleSelection(item.id)
    return
  }
  resetProcessingContext()
  activeReferenceId.value = item.id
  void focusAdminSection('review')
}

function toggleSelection(feedbackId: string): void {
  if (!selectedIds.value.length) {
    resetProcessingContext()
  }

  if (selectedIds.value.includes(feedbackId)) {
    selectedIds.value = selectedIds.value.filter((id) => id !== feedbackId)
    return
  }
  selectedIds.value = [...selectedIds.value, feedbackId]
  void focusAdminSection('review')
}

function resetDraftEditor(): void {
  currentDraftId.value = ''
  currentDraftRecord.value = null
  submissionResult.value = null
  draftForm.title = draftPreviewTitle.value
  draftForm.body_markdown = '摘要\n\n关联标识\n\n用户信号数量'
}

function resetProcessingContext(): void {
  activeBatchId.value = ''
  resetDraftEditor()
}

async function loadFeedbackByStatus(status: QueueStatus): Promise<FeedbackItem[]> {
  const response = await apiGet<PaginatedResponse<FeedbackItem>>(buildAdminApiPath(`/feedback?status=${status}`))
  return response.success ? response.data.items : []
}

async function loadAdminData(): Promise<void> {
  if (!isAdminUnlocked.value) {
    return
  }
  loading.value = true
  const [pending, grouped, submitted] = await Promise.all([
    loadFeedbackByStatus('pending'),
    loadFeedbackByStatus('grouped'),
    loadFeedbackByStatus('submitted'),
  ])
  pendingItems.value = pending
  groupedItems.value = grouped
  submittedItems.value = submitted
  selectedIds.value = selectedIds.value.filter((id) => pendingItems.value.some((item) => item.id === id))
  if (activeReferenceId.value && !queueItems.value.some((item) => item.id === activeReferenceId.value)) {
    activeReferenceId.value = ''
  }
  loading.value = false
}

async function unlockAdmin(): Promise<void> {
  const token = adminTokenInput.value.trim()
  if (!token) {
    adminAuthMessage.value = '请输入管理 token。'
    return
  }

  setAdminToken(token)
  isAdminUnlocked.value = true
  adminAuthMessage.value = ''
  await loadAdminData()
  await nextTick()
  setupSectionObserver()
}

async function createBatch(): Promise<void> {
  if (!selectedIds.value.length) {
    batchMessage.value = '请先选择至少一条反馈。'
    return
  }

  creatingBatch.value = true
  batchMessage.value = ''

  const payload: DraftBatchCreatePayload = {
    feedback_item_ids: selectedIds.value,
    confirm_mixed_related_ids: batchSummary.value.isMixed,
  }
  const response = await apiPost<DraftBatchCreateResponse, DraftBatchCreatePayload>(buildAdminApiPath('/draft-batches'), payload)

  if (response.success) {
    batchMessage.value = `批次创建成功：${response.data.id}`
    activeBatchId.value = response.data.id
    selectedIds.value = []
    resetDraftEditor()
    await loadAdminData()
    await focusAdminSection('draft')
  } else {
    batchMessage.value = response.message || '批次创建失败'
  }

  creatingBatch.value = false
}

async function loadDraft(draftId: string): Promise<void> {
  const response = await apiGet<DraftRecord>(buildAdminApiPath(`/drafts/${draftId}`))
  if (response.success) {
    currentDraftId.value = response.data.id
    currentDraftRecord.value = response.data
    draftForm.title = response.data.title
    draftForm.body_markdown = response.data.body_markdown
    submissionResult.value = null
    await focusAdminSection('draft')
    draftMessage.value = `草稿已加载，更新时间 ${response.data.updated_at}`
  } else {
    draftMessage.value = response.message || '草稿加载失败'
  }
}

async function integrateDraft(): Promise<void> {
  if (!activeBatchId.value) {
    batchMessage.value = '请先创建批次。'
    return
  }

  integratingDraft.value = true
  draftMessage.value = ''
  const response = await apiPost<DraftIntegrateResponse, Record<string, never>>(
    buildAdminApiPath(`/draft-batches/${activeBatchId.value}/integrate`),
    {},
  )

  if (response.success) {
    await loadDraft(response.data.draft_id)
  } else {
    draftMessage.value = response.message || '草稿生成失败'
  }

  integratingDraft.value = false
}

async function saveDraft(): Promise<void> {
  if (!currentDraftId.value) {
    draftMessage.value = '请先生成草稿。'
    return
  }

  savingDraft.value = true
  const payload: DraftUpdatePayload = {
    title: draftForm.title,
    body_markdown: draftForm.body_markdown,
  }
  const response = await apiPut<{ id: string; status: string; updated_at: string }, DraftUpdatePayload>(
    buildAdminApiPath(`/drafts/${currentDraftId.value}`),
    payload,
  )

  if (response.success) {
    currentDraftRecord.value = {
      ...(currentDraftRecord.value || {
        id: currentDraftId.value,
        batch_id: activeBatchId.value,
        title: draftForm.title,
        body_markdown: draftForm.body_markdown,
        related_id_summary: draftRelatedIdSummary.value,
        status: response.data.status,
        updated_at: response.data.updated_at,
      }),
      title: draftForm.title,
      body_markdown: draftForm.body_markdown,
      status: response.data.status,
      updated_at: response.data.updated_at,
    }
  }

  draftMessage.value = response.success
    ? `草稿保存成功，更新时间 ${response.data.updated_at}`
    : response.message || '草稿保存失败'
  savingDraft.value = false
}

async function submitDraftToGithub(): Promise<void> {
  if (!currentDraftId.value) {
    draftMessage.value = '请先生成草稿。'
    return
  }

  submittingDraft.value = true
  const response = await apiPost<DraftSubmitResponse, Record<string, never>>(
    buildAdminApiPath(`/drafts/${currentDraftId.value}/submit`),
    {},
  )

  if (response.success) {
    submissionResult.value = response.data
    draftMessage.value = `草稿已提交，GitHub Issue #${response.data.issue_number}`
    await loadAdminData()
    await focusAdminSection('draft')
  } else {
    draftMessage.value = response.message || '提交失败'
  }

  submittingDraft.value = false
}

function setupSectionObserver(): void {
  if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined') {
    return
  }

  const sections = [
    { id: 'queue-panel', section: 'queue' as const },
    { id: 'review-panel', section: 'review' as const },
    { id: 'draft-panel', section: 'draft' as const },
  ]

  sectionObserver = new IntersectionObserver(
    (entries) => {
      const visibleEntry = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0]

      if (!visibleEntry) {
        return
      }

      const matchedSection = sections.find((item) => item.id === visibleEntry.target.id)
      if (matchedSection) {
        activeAdminSection.value = matchedSection.section
      }
    },
    {
      threshold: [0.35, 0.55, 0.75],
      rootMargin: '-10% 0px -45% 0px',
    },
  )

  sections.forEach((item) => {
    const element = document.getElementById(item.id)
    if (element) {
      sectionObserver?.observe(element)
    }
  })
}

onMounted(async () => {
  if (isAdminUnlocked.value) {
    await loadAdminData()
    await nextTick()
    setupSectionObserver()
  }
})

onBeforeUnmount(() => {
  sectionObserver?.disconnect()
})
</script>
