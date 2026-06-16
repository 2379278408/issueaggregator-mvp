<template>
  <AppShell
    title="Issue Triage Studio"
    description="整理反馈，生成 GitHub Issue 草稿。"
    wide
  >
    <section v-if="!isAdminUnlocked" class="admin-auth-screen">
      <AdminLoginCard
        :auth-message="adminAuthMessage"
        :is-logging-in="isLoggingIn"
        @submit="unlockAdmin"
      />
    </section>

    <section v-else class="triage-studio">
      <header class="triage-studio__header">
        <div>
          <p class="eyebrow">Private Studio</p>
          <h2>整理反馈，生成 Issue</h2>
          <p>左侧导航负责切换工作区，中间专注当前操作，右侧始终保留批次上下文和推进状态。</p>
        </div>
        <div class="triage-studio__header-meta">
          <div class="triage-studio__summary-pill">
            <span>管理员</span>
            <strong>{{ adminUsername || '-' }}</strong>
          </div>
          <div class="triage-studio__summary-pill">
            <span>当前焦点</span>
            <strong>{{ activeAdminSectionLabel }}</strong>
          </div>
          <div class="triage-studio__summary-pill triage-studio__summary-pill--accent">
            <span>当前队列</span>
            <strong>{{ queueHeading }}</strong>
          </div>
          <button class="button button--subtle" type="button" @click="handleAdminLogout">登出</button>
        </div>
      </header>

      <div v-if="adminDataMessage" class="feedback-message feedback-message--error">{{ adminDataMessage }}</div>

      <section class="triage-layout admin-layout">
        <section class="triage-main">
          <section class="triage-grid">
            <FeedbackQueue
              :queue-status="queueStatus"
              :items="queueItems"
              :sections="queueSections"
              :selected-ids="selectedIds"
              :loading="loading"
              :status-counts="statusCounts"
              :heading="queueHeading"
              :description="queueDescription"
              :all-selected="allPendingSelected"
              :active-section="activeAdminSection"
              :review-item-count="reviewItems.length"
              :current-draft-id="currentDraftId"
              :audit-event-count="auditEvents.length"
              @switch-queue="switchQueue"
              @toggle-selection="toggleSelection"
              @item-click="handleQueueItemClick"
              @toggle-select-all="toggleCurrentPendingSelection"
              @focus-section="focusAdminSection"
            />

            <div class="triage-workbench">
          <ReviewPanel
            :items="reviewItems"
            :headline="reviewHeadline"
            :description="reviewDescription"
            :decision="reviewDecision"
            :decision-tone-class="reviewDecisionToneClass"
            :primary-related-id="activeReferenceRelatedId"
            :missing-count="reviewMissingCount"
            :message="batchMessage"
            :creating-batch="creatingBatch"
            :integrating-draft="integratingDraft"
            :queue-status="queueStatus"
            :active-batch-id="activeBatchId"
            :is-mixed="batchSummary.isMixed"
            @create-batch="createBatch"
            @integrate-draft="integrateDraft"
          />

          <DraftEditor
            :active-batch-id="activeBatchId"
            :current-draft-id="currentDraftId"
            :draft-form="{ title: draftForm.title, body_markdown: draftForm.body_markdown }"
            :submission-result="submissionResult"
            :status-label="draftStatusLabel"
            :status-description="draftStatusDescription"
            :related-id-summary="draftRelatedIdSummary"
            :updated-at-label="draftUpdatedAtLabel"
            :editor-headline="draftEditorHeadline"
            :editor-hint="draftEditorHint"
            :show-checklist="showDraftSubmissionChecklist"
            :checklist-summary="draftSubmissionChecklistSummary"
            :review-items="reviewItems"
            :related-id-count="batchSummary.relatedIdCount"
            :title-length="draftTitleLength"
            :body-length="draftBodyLength"
            :section-count="draftSectionCount"
            :can-submit="draftCanSubmit"
            :message="draftMessage"
            :saving-draft="savingDraft"
            :submitting-draft="submittingDraft"
            :integrating-draft="integratingDraft"
            @update:draft-form="onDraftFormUpdate"
            @integrate-draft="integrateDraft"
            @save-draft="saveDraft"
            @submit-draft="submitDraftToGithub"
          />

          <AuditPanel
            :events="auditEvents"
            :filter-options="auditFilterOptions"
            :time-range-options="auditTimeRangeOptions"
            :active-filter="activeAuditFilter"
            :active-time-range="activeAuditTimeRange"
            :keyword-input="auditKeywordInput"
            :loading="loadingAuditEvents"
            :message="auditMessage"
            @refresh="loadAuditEvents"
            @apply-filter="applyAuditFilter"
            @apply-time-range="applyAuditTimeRange"
            @apply-keyword="applyAuditKeyword"
            @update:keyword-input="onAuditKeywordInput"
          />
        </div>
          </section>
        </section>

        <aside class="triage-context" aria-label="当前工作上下文">
        <section class="triage-context__panel">
          <div class="studio-section-head studio-section-head--stacked">
            <div>
              <span>Workflow Rail</span>
              <h3>推进状态</h3>
            </div>
            <p>始终查看当前工作流停在哪一步，以及下一步动作是什么。</p>
          </div>
          <div class="workflow-rail">
            <article v-for="step in workflowSteps" :key="step.index" class="workflow-step" :class="step.state">
              <span>{{ step.index }}</span>
              <strong>{{ step.label }}</strong>
            </article>
          </div>
        </section>

        <section class="triage-context__panel triage-context__panel--accent">
          <div class="studio-section-head studio-section-head--stacked">
            <div>
              <span>Live Context</span>
              <h3>{{ contextPanelTitle }}</h3>
            </div>
            <p>{{ contextPanelDescription }}</p>
          </div>
          <div class="triage-context__facts">
            <article>
              <span>当前队列</span>
              <strong>{{ queueHeading }}</strong>
            </article>
            <article>
              <span>主关联标识</span>
              <strong>{{ contextPrimaryRelatedId }}</strong>
            </article>
            <article>
              <span>当前条目数</span>
              <strong>{{ reviewItems.length }}</strong>
            </article>
            <article>
              <span>缺失字段</span>
              <strong>{{ reviewMissingCount }}</strong>
            </article>
          </div>
          <div class="triage-context__subhead">
            <span>Batch Snapshot</span>
            <strong>批次速览</strong>
          </div>
          <dl class="triage-context__snapshot">
            <div>
              <dt>批次 ID</dt>
              <dd>{{ activeBatchId || '待创建' }}</dd>
            </div>
            <div>
              <dt>草稿状态</dt>
              <dd>{{ draftStatusLabel }}</dd>
            </div>
            <div>
              <dt>草稿标识</dt>
              <dd>{{ draftRelatedIdSummary }}</dd>
            </div>
            <div>
              <dt>最近更新</dt>
              <dd>{{ draftUpdatedAtLabel }}</dd>
            </div>
          </dl>
        </section>
      </aside>
      </section>
    </section>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '../components/layout/AppShell.vue'
import AdminLoginCard from '../components/admin/AdminLoginCard.vue'
import AuditPanel from '../components/admin/AuditPanel.vue'
import DraftEditor from '../components/admin/DraftEditor.vue'
import type { DraftForm } from '../components/admin/DraftEditor.vue'
import FeedbackQueue from '../components/admin/FeedbackQueue.vue'
import type { AdminSection, QueueStatus } from '../components/admin/FeedbackQueue.vue'
import ReviewPanel from '../components/admin/ReviewPanel.vue'
import type { AuditEventFilter, AuditTimeRange } from '../components/admin/AuditPanel.vue'
import {
  adminLogin,
  adminLogout,
  adminSessionMe,
  apiGet,
  apiPost,
  apiPut,
  buildAdminApiPath,
  clearAdminToken,
  hasAdminToken,
  setAdminToken,
  type AuditEventRecord,
  type DraftBatchCreatePayload,
  type DraftBatchCreateResponse,
  type DraftIntegrateResponse,
  type DraftRecord,
  type DraftSubmitResponse,
  type DraftUpdatePayload,
  type FeedbackItem,
  type PaginatedResponse,
} from '../services/api'

const typeLabelMap: Record<string, string> = {
  bug: '缺陷', feature: '新功能', enhancement: '优化', question: '问题',
}

const statusLabelMap: Record<string, QueueStatus> & Record<string, string> = {
  pending: '待处理', grouped: '已分组', submitted: '已提交',
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
const loadingAuditEvents = ref(false)
const batchMessage = ref('')
const draftMessage = ref('')
const auditMessage = ref('')
const activeBatchId = ref('')
const currentDraftId = ref('')
const submissionResult = ref<DraftSubmitResponse | null>(null)
const currentDraftRecord = ref<DraftRecord | null>(null)
const auditEvents = ref<AuditEventRecord[]>([])
const activeAuditFilter = ref<AuditEventFilter>('all')
const activeAuditTimeRange = ref<AuditTimeRange>('all')
const auditKeyword = ref('')
const auditKeywordInput = ref('')
const isAdminUnlocked = ref(hasAdminToken())
const adminUsernameInput = ref('')
const adminPasswordInput = ref('')
const adminUsername = ref<string | null>(null)
const isLoggingIn = ref(false)
const adminAuthMessage = ref('')
const adminDataMessage = ref('')
const route = useRoute()
const router = useRouter()

const draftForm = reactive<DraftUpdatePayload>({
  title: '[草稿] 请选择反馈后生成标题',
  body_markdown: '摘要\n\n关联标识\n\n用户信号数量',
})

const auditFilterOptions: Array<{ value: AuditEventFilter; label: string }> = [
  { value: 'all', label: '全部事件' },
  { value: 'admin_auth_failed', label: '鉴权失败' },
  { value: 'admin_action_succeeded', label: '成功操作' },
]

const auditTimeRangeOptions: Array<{ value: AuditTimeRange; label: string }> = [
  { value: 'all', label: '全部时间' },
  { value: '10m', label: '10 分钟' },
  { value: '1h', label: '1 小时' },
  { value: '24h', label: '24 小时' },
]

const statusCounts = computed(() => ({
  pending: pendingItems.value.length,
  grouped: groupedItems.value.length,
  submitted: submittedItems.value.length,
}))

const selectedItems = computed(() => pendingItems.value.filter((item) => selectedIds.value.includes(item.id)))

const queueItems = computed(() => {
  if (queueStatus.value === 'grouped') return groupedItems.value
  if (queueStatus.value === 'submitted') return submittedItems.value
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

const activeBatchItems = computed(() => {
  if (!activeBatchId.value) return [] as FeedbackItem[]
  return queueItems.value.filter((item) => item.batch_id === activeBatchId.value)
})

const allPendingSelected = computed(() => {
  if (queueStatus.value !== 'pending' || !queueItems.value.length) return false
  return queueItems.value.every((item) => selectedIds.value.includes(item.id))
})

const reviewItems = computed(() => {
  if (queueStatus.value === 'pending') return selectedItems.value
  if (activeBatchItems.value.length) return activeBatchItems.value
  return activeReferenceItem.value ? [activeReferenceItem.value] : []
})

const activeReviewRelatedIds = computed(() => [...new Set(reviewItems.value.map((item) => item.related_id))])

const batchSummary = computed(() => {
  const relatedIds = [...new Set(selectedItems.value.map((item) => item.related_id))]
  return {
    primaryRelatedId: relatedIds.length === 1 ? relatedIds[0] : null,
    itemCount: selectedItems.value.length,
    isMixed: relatedIds.length > 1,
    relatedIdCount: relatedIds.length,
  }
})

const activeReferenceRelatedId = computed(() => {
  if (activeReviewRelatedIds.value.length === 1) return activeReviewRelatedIds.value[0]
  return activeReferenceItem.value?.related_id || ''
})

const reviewMissingCount = computed(() => reviewItems.value.reduce((total, item) => total + getMissingFieldCount(item), 0))

const reviewDecision = computed(() => {
  let title: string, description: string
  if (queueStatus.value !== 'pending') {
    title = reviewItems.value.length ? '当前批次可作为回看参考' : '等待选择参考记录'
    description = reviewItems.value.length
      ? `当前批次共包含 ${reviewItems.value.length} 条反馈，可直接回看聚合结果与草稿上下文。`
      : '从左侧已分组或已提交队列选择一条记录，这里会显示决策判断。'
  } else if (!selectedItems.value.length) {
    title = '先选择要进入本轮判断的反馈'
    description = '从左侧收件箱中勾选反馈，系统会给出是否适合建批、是否建议拆分以及缺失信息提示。'
  } else if (batchSummary.value.isMixed) {
    title = '当前反馈涉及多个关联标识，建议拆分主题'
    description = `当前共包含 ${batchSummary.value.relatedIdCount} 个关联标识，拆成多个批次更利于后续草稿聚合和提交。`
  } else if (reviewMissingCount.value > 0) {
    title = '当前主题集中，但存在待补充信息'
    description = `当前主题已经集中，但还有 ${reviewMissingCount.value} 处关键信息待补充，草稿阶段需要人工修订。`
  } else {
    title = '当前反馈可以直接进入建批'
    description = '关联标识一致，关键信息完整度也足够，可以直接创建批次并生成草稿。'
  }
  return { title, description }
})

const reviewDecisionToneClass = computed(() => {
  if (queueStatus.value !== 'pending') return 'is-neutral'
  if (!selectedItems.value.length) return 'is-idle'
  if (batchSummary.value.isMixed) return 'is-warning'
  if (reviewMissingCount.value > 0) return 'is-caution'
  return 'is-ready'
})

const draftStatusLabel = computed(() => {
  if (submissionResult.value) return '已提交'
  if (currentDraftRecord.value?.status === 'draft_ready' || currentDraftId.value) return '待提交'
  if (activeBatchId.value) return '待生成'
  return '未开始'
})

const draftStatusDescription = computed(() => {
  if (submissionResult.value) return `GitHub Issue #${submissionResult.value.issue_number} 已创建，可继续回看本次处理记录。`
  if (currentDraftId.value) return '草稿已经生成。这里保留当前批次的唯一编辑上下文，适合人工修订后直接提交。'
  if (activeBatchId.value) return '批次已经创建，下一步生成结构化草稿。'
  return '先从左侧队列选择反馈并创建批次，这里会进入草稿编辑状态。'
})

const draftRelatedIdSummary = computed(() => {
  if (submissionResult.value?.related_id) return submissionResult.value.related_id
  if (currentDraftRecord.value?.related_id_summary) return currentDraftRecord.value.related_id_summary
  return batchSummary.value.primaryRelatedId || activeReferenceRelatedId.value || '待确认'
})

const draftUpdatedAtLabel = computed(() => {
  if (submissionResult.value?.submitted_at) return submissionResult.value.submitted_at
  if (currentDraftRecord.value?.updated_at) return currentDraftRecord.value.updated_at
  return '尚未生成'
})

const draftEditorHeadline = computed(() => {
  if (submissionResult.value) return 'GitHub 提交已完成'
  if (!activeBatchId.value) return '等待进入草稿阶段'
  if (!currentDraftId.value) return '先生成草稿，再进入编辑'
  return '当前草稿可直接继续完善'
})

const draftEditorHint = computed(() => {
  if (submissionResult.value) return '当前版本已经提交成功，可以继续回看正文结构或切换到其他批次。'
  if (!activeBatchId.value) return '左侧完成建批后，这里会出现标题、正文和提交动作。'
  if (!currentDraftId.value) return '生成后的草稿会自动带入批次上下文，便于你继续整理 Markdown 内容。'
  return '保持标题简短，正文按章节展开，保存后再提交到 GitHub。'
})

const draftTitleLength = computed(() => draftForm.title.trim().length)
const draftBodyLength = computed(() => draftForm.body_markdown.trim().length)
const draftSectionCount = computed(() => {
  const matches = draftForm.body_markdown.match(/^##\s+/gm)
  return matches?.length || 0
})

const showDraftSubmissionChecklist = computed(() => Boolean(currentDraftId.value) && !submissionResult.value)

const draftSubmissionChecklistSummary = computed(() => {
  if (!currentDraftId.value) return '生成草稿后，这里会显示提交前需要确认的关键信息。'
  return `当前草稿关联 ${draftRelatedIdSummary.value}，覆盖 ${reviewItems.value.length} 条反馈。保存后可直接提交到 GitHub。`
})

const draftCanSubmit = computed(() => Boolean(currentDraftId.value) && Boolean(draftForm.title.trim()) && Boolean(draftForm.body_markdown.trim()))

const queueHeading = computed(() => statusLabelMap[queueStatus.value] || queueStatus.value)

const queueDescription = computed(() => {
  if (queueStatus.value === 'grouped') return '查看已进入批次、等待继续处理的反馈。'
  if (queueStatus.value === 'submitted') return '查看已经完成提交的反馈记录。'
  return '勾选同一主题的反馈，准备创建批次。'
})

const reviewHeadline = computed(() => {
  if (queueStatus.value === 'pending') return selectedItems.value.length ? '当前选中反馈' : '等待选择反馈'
  return reviewItems.value.length ? '当前批次反馈' : '等待选择参考项'
})

const reviewDescription = computed(() => {
  if (queueStatus.value === 'pending') {
    return selectedItems.value.length ? '确认这些反馈是否属于同一主题，再创建批次。' : '从左侧队列中选择待处理反馈，这里会显示原始内容和补充信息。'
  }
  return reviewItems.value.length ? '这里展示当前批次中的全部反馈，便于统一回看聚合结果。' : '从左侧已分组或已提交队列选择一条记录，这里会显示详情。'
})

const workflowSteps = computed(() => [
  { index: '1', label: '选中反馈', state: selectedItems.value.length ? 'is-done' : 'is-current' },
  { index: '2', label: '创建批次', state: activeBatchId.value ? 'is-done' : 'is-idle' },
  { index: '3', label: '生成草稿', state: currentDraftId.value ? 'is-done' : 'is-idle' },
  { index: '4', label: '提交 GitHub', state: submissionResult.value ? 'is-done' : 'is-idle' },
])

const activeAdminSectionLabel = computed(() => {
  if (activeAdminSection.value === 'audit') return '审计与安全'
  if (activeAdminSection.value === 'review') return '聚合审阅'
  if (activeAdminSection.value === 'draft') return '草稿与提交'
  return '反馈队列'
})

const contextPrimaryRelatedId = computed(() => {
  if (draftRelatedIdSummary.value && draftRelatedIdSummary.value !== '待确认') return draftRelatedIdSummary.value
  if (batchSummary.value.primaryRelatedId) return batchSummary.value.primaryRelatedId
  if (activeReferenceRelatedId.value) return activeReferenceRelatedId.value
  return '待确认'
})

const contextPanelTitle = computed(() => {
  if (activeAdminSection.value === 'audit') return '回看安全链路'
  if (activeAdminSection.value === 'draft') return submissionResult.value ? '已完成提交' : '准备编辑与提交'
  if (activeAdminSection.value === 'review') return reviewItems.value.length ? '当前主题判断中' : '等待进入主题判断'
  return queueStatus.value === 'pending' ? '待整理反馈收件箱' : '历史批次回看模式'
})

const contextPanelDescription = computed(() => {
  if (activeAdminSection.value === 'audit') return '这里主要用于确认管理员操作是否完整落库，以及近期是否存在异常鉴权。'
  if (activeAdminSection.value === 'draft') return submissionResult.value
    ? '当前批次已经提交到 GitHub，可以继续检查结果或切换到新的批次。'
    : '草稿编辑区已经接管主流程，接下来重点确认标题、正文和提交状态。'
  if (activeAdminSection.value === 'review') return reviewItems.value.length
    ? '当前区块用于判断这些反馈是否属于同一主题，并确定是否适合建批。'
    : '先从左侧队列中勾选或选中反馈，系统才会生成主题判断。'
  return queueStatus.value === 'pending'
    ? '优先在这里完成勾选和粗分组，避免把太多信息直接堆进后续编辑区。'
    : '当前处于历史回看模式，重点是沿着已分组或已提交链路快速回到对应草稿。'
})

let sectionObserver: IntersectionObserver | null = null

function getMissingFieldCount(item: FeedbackItem): number {
  let count = 0
  if (!item.expected_behavior) count += 1
  if (!item.actual_behavior) count += 1
  return count
}

function toComparableDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function getQueueTimeBucket(item: FeedbackItem): '今天' | '最近 7 天' | '更早' | '未标注时间' {
  const value = item.submitted_at || item.created_at
  const timestamp = toComparableDate(value)
  if (!timestamp) return '未标注时间'
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const sevenDaysAgo = new Date(startOfToday)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 6)
  if (timestamp >= startOfToday) return '今天'
  if (timestamp >= sevenDaysAgo) return '最近 7 天'
  return '更早'
}

function parseAuditFilter(value: unknown): AuditEventFilter {
  return value === 'admin_auth_failed' || value === 'admin_action_succeeded' ? value : 'all'
}

function parseAuditTimeRange(value: unknown): AuditTimeRange {
  return value === '10m' || value === '1h' || value === '24h' ? value : 'all'
}

function parseAuditKeyword(value: unknown): string {
  return typeof value === 'string' ? value.trim().slice(0, 120) : ''
}

function parseQueueStatus(value: unknown): QueueStatus {
  return value === 'grouped' || value === 'submitted' ? value : 'pending'
}

function parseContextId(value: unknown): string {
  return typeof value === 'string' ? value.trim().slice(0, 64) : ''
}

function getAdminRouteContext() {
  return {
    queueStatus: parseQueueStatus(route.query.adminQueue),
    batchId: parseContextId(route.query.batchId),
    draftId: parseContextId(route.query.draftId),
  }
}

function syncAdminContextToRoute(): void {
  const nextQuery = { ...route.query }
  if (queueStatus.value === 'pending') delete nextQuery.adminQueue
  else nextQuery.adminQueue = queueStatus.value
  if (!activeBatchId.value) delete nextQuery.batchId
  else nextQuery.batchId = activeBatchId.value
  if (!currentDraftId.value) delete nextQuery.draftId
  else nextQuery.draftId = currentDraftId.value
  void router.replace({ query: nextQuery })
}

function syncAuditFiltersToRoute(): void {
  const nextQuery = { ...route.query }
  if (activeAuditFilter.value === 'all') delete nextQuery.auditEventType
  else nextQuery.auditEventType = activeAuditFilter.value
  if (activeAuditTimeRange.value === 'all') delete nextQuery.auditTimeRange
  else nextQuery.auditTimeRange = activeAuditTimeRange.value
  if (!auditKeyword.value) delete nextQuery.auditKeyword
  else nextQuery.auditKeyword = auditKeyword.value
  void router.replace({ query: nextQuery })
}

function restoreAuditFiltersFromRoute(): void {
  activeAuditFilter.value = parseAuditFilter(route.query.auditEventType)
  activeAuditTimeRange.value = parseAuditTimeRange(route.query.auditTimeRange)
  auditKeyword.value = parseAuditKeyword(route.query.auditKeyword)
  auditKeywordInput.value = auditKeyword.value
}

function restoreQueueStatusFromRoute(): void {
  queueStatus.value = getAdminRouteContext().queueStatus
}

function switchQueue(status: QueueStatus): void {
  queueStatus.value = status
  activeAdminSection.value = 'queue'
  activeReferenceId.value = ''
  batchMessage.value = ''
  draftMessage.value = ''
  resetProcessingContext()
  if (status !== 'pending') selectedIds.value = []
  syncAdminContextToRoute()
}

async function focusAdminSection(section: AdminSection): Promise<void> {
  activeAdminSection.value = section
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  await nextTick()
  const elementId = section === 'queue' ? 'queue-panel'
    : section === 'review' ? 'review-panel'
    : section === 'draft' ? 'draft-panel'
    : 'audit-panel'
  const element = document.getElementById(elementId)
  if (!element) return
  element.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
  activeBatchId.value = item.batch_id || ''
  if (item.draft_id) {
    void loadDraft(item.draft_id)
    return
  }
  if (item.batch_integration_error) {
    draftMessage.value = `上次生成失败：${item.batch_integration_error}。可重新生成草稿。`
  }
  syncAdminContextToRoute()
  void focusAdminSection('review')
}

function toggleSelection(feedbackId: string): void {
  if (!selectedIds.value.length) resetProcessingContext()
  if (selectedIds.value.includes(feedbackId)) {
    selectedIds.value = selectedIds.value.filter((id) => id !== feedbackId)
    return
  }
  selectedIds.value = [...selectedIds.value, feedbackId]
  void focusAdminSection('review')
}

function toggleCurrentPendingSelection(): void {
  if (queueStatus.value !== 'pending') return
  if (allPendingSelected.value) {
    selectedIds.value = []
    resetProcessingContext()
    return
  }
  resetProcessingContext()
  selectedIds.value = queueItems.value.map((item) => item.id)
  void focusAdminSection('review')
}

function resetDraftEditor(): void {
  currentDraftId.value = ''
  currentDraftRecord.value = null
  submissionResult.value = null
  draftForm.title = draftPreviewTitle.value
  draftForm.body_markdown = '摘要\n\n关联标识\n\n用户信号数量'
}

const draftPreviewTitle = computed(() => {
  if (currentDraftId.value) return draftForm.title
  if (!selectedItems.value.length) return '[草稿] 请选择反馈后生成标题'
  if (batchSummary.value.primaryRelatedId) return `[草稿] ${batchSummary.value.primaryRelatedId}`
  return '[草稿] 混合关联标识批次'
})

function resetProcessingContext(): void {
  activeBatchId.value = ''
  resetDraftEditor()
  syncAdminContextToRoute()
}

function clearAdminQueueState(): void {
  pendingItems.value = []
  groupedItems.value = []
  submittedItems.value = []
  selectedIds.value = []
  activeReferenceId.value = ''
}

function clearAuditState(): void {
  auditEvents.value = []
  auditMessage.value = ''
  activeAuditFilter.value = 'all'
  activeAuditTimeRange.value = 'all'
  auditKeyword.value = ''
  auditKeywordInput.value = ''
}

function clearAdminWorkspaceState(): void {
  clearAdminQueueState()
  clearAuditState()
  batchMessage.value = ''
  draftMessage.value = ''
  resetProcessingContext()
}

function relockAdmin(message: string): void {
  clearAdminToken()
  sectionObserver?.disconnect()
  isAdminUnlocked.value = false
  adminDataMessage.value = ''
  adminAuthMessage.value = message
  clearAdminWorkspaceState()
}

function getResponseErrorStatus(response: { success: boolean; http_status?: number }): number | undefined {
  return response.success ? undefined : response.http_status
}

function getErrorHttpStatus(error: unknown): number | undefined {
  if (typeof error !== 'object' || !error || !('httpStatus' in error)) return undefined
  const status = (error as { httpStatus?: unknown }).httpStatus
  return typeof status === 'number' ? status : undefined
}

function isAuthFailureStatus(status: number | undefined): boolean {
  return status === 401 || status === 403
}

async function loadFeedbackByStatus(status: QueueStatus): Promise<FeedbackItem[]> {
  const response = await apiGet<PaginatedResponse<FeedbackItem>>(buildAdminApiPath(`/feedback?status=${status}`))
  if (!response.success) {
    throw Object.assign(new Error(response.message || 'Failed to load feedback'), { httpStatus: getResponseErrorStatus(response) })
  }
  return response.data.items
}

async function loadAuditEvents(): Promise<void> {
  if (!isAdminUnlocked.value) return
  loadingAuditEvents.value = true
  auditMessage.value = ''
  try {
    const searchParams = new URLSearchParams({ page_size: '8' })
    if (activeAuditFilter.value !== 'all') searchParams.set('event_type', activeAuditFilter.value)
    if (activeAuditTimeRange.value !== 'all') searchParams.set('time_range', activeAuditTimeRange.value)
    if (auditKeyword.value) searchParams.set('keyword', auditKeyword.value)
    const response = await apiGet<PaginatedResponse<AuditEventRecord>>(buildAdminApiPath(`/audit-events?${searchParams.toString()}`))
    if (response.success) { auditEvents.value = response.data.items; return }
    auditEvents.value = []
    auditMessage.value = response.message || '审计事件加载失败，请稍后重试。'
  } catch {
    auditEvents.value = []
    auditMessage.value = '审计事件加载失败，请稍后重试。'
  } finally {
    loadingAuditEvents.value = false
  }
}

async function applyAuditFilter(filter: AuditEventFilter): Promise<void> {
  if (activeAuditFilter.value === filter) return
  activeAuditFilter.value = filter
  syncAuditFiltersToRoute()
  await loadAuditEvents()
}

async function applyAuditTimeRange(timeRange: AuditTimeRange): Promise<void> {
  if (activeAuditTimeRange.value === timeRange) return
  activeAuditTimeRange.value = timeRange
  syncAuditFiltersToRoute()
  await loadAuditEvents()
}

async function applyAuditKeyword(keyword?: string): Promise<void> {
  if (keyword !== undefined) {
    auditKeywordInput.value = keyword
  }
  auditKeyword.value = auditKeywordInput.value.trim()
  syncAuditFiltersToRoute()
  await loadAuditEvents()
}

function onAuditKeywordInput(value: string): void {
  auditKeywordInput.value = value
}

function onDraftFormUpdate(form: DraftForm): void {
  if (form.title) draftForm.title = form.title
  if (form.body_markdown) draftForm.body_markdown = form.body_markdown
}

async function loadAdminData(options: { relockOnAuthFailure?: boolean } = {}): Promise<boolean> {
  if (!isAdminUnlocked.value) return false
  loading.value = true
  try {
    adminDataMessage.value = ''
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
    syncAdminContextToRoute()
    return true
  } catch (error) {
    if (options.relockOnAuthFailure && isAuthFailureStatus(getErrorHttpStatus(error))) {
      relockAdmin('登录态已失效，请重新登录。')
      return false
    }
    clearAdminQueueState()
    adminDataMessage.value = '管理数据加载失败，请检查后端服务。'
    return false
  } finally {
    loading.value = false
  }
}

async function unlockAdmin(username: string, password: string): Promise<void> {
  if (!username || !password) {
    adminAuthMessage.value = '请输入用户名和密码。'
    return
  }
  isLoggingIn.value = true
  adminAuthMessage.value = ''
  try {
    const result = await adminLogin(username, password)
    if (!result.success) {
      const message = result.error_code === 'ADMIN_LOGIN_COOLDOWN_ACTIVE'
        ? result.message || '登录冷却中，请稍后重试。'
        : '用户名或密码错误。'
      adminAuthMessage.value = message
      return
    }
    adminUsername.value = result.data.username
    isAdminUnlocked.value = true
    setAdminToken('session-active')
    const loaded = await loadAdminData({ relockOnAuthFailure: true })
    if (!loaded) return
    await loadAuditEvents()
    await nextTick()
    setupSectionObserver()
  } finally {
    isLoggingIn.value = false
  }
}

async function handleAdminLogout(): Promise<void> {
  try { await adminLogout() } finally {
    clearAdminToken()
    isAdminUnlocked.value = false
    adminUsername.value = null
    adminAuthMessage.value = ''
    clearAdminWorkspaceState()
  }
}

async function createBatch(): Promise<void> {
  if (!selectedIds.value.length) { batchMessage.value = '请先选择至少一条反馈。'; return }
  creatingBatch.value = true
  batchMessage.value = ''
  const payload: DraftBatchCreatePayload = { feedback_item_ids: selectedIds.value, confirm_mixed_related_ids: batchSummary.value.isMixed }
  try {
    const response = await apiPost<DraftBatchCreateResponse, DraftBatchCreatePayload>(buildAdminApiPath('/draft-batches'), payload)
    if (response.success) {
      batchMessage.value = `批次创建成功：${response.data.id}`
      activeBatchId.value = response.data.id
      queueStatus.value = 'grouped'
      selectedIds.value = []
      resetDraftEditor()
      await loadAdminData()
      const firstGroupedItem = groupedItems.value.find((item) => item.batch_id === response.data.id)
      activeReferenceId.value = firstGroupedItem?.id || ''
      syncAdminContextToRoute()
      await focusAdminSection('draft')
    } else {
      batchMessage.value = response.message || '批次创建失败'
    }
  } catch {
    batchMessage.value = '批次创建失败，请检查网络后重试。'
  } finally {
    creatingBatch.value = false
  }
}

async function loadDraft(draftId: string): Promise<void> {
  try {
    const response = await apiGet<DraftRecord>(buildAdminApiPath(`/drafts/${draftId}`))
    if (response.success) {
      currentDraftId.value = response.data.id
      currentDraftRecord.value = response.data
      draftForm.title = response.data.title
      draftForm.body_markdown = response.data.body_markdown
      submissionResult.value = null
      syncAdminContextToRoute()
      await focusAdminSection('draft')
      draftMessage.value = `草稿已加载，更新时间 ${response.data.updated_at}`
    } else {
      draftMessage.value = response.message || '草稿加载失败'
    }
  } catch {
    draftMessage.value = '草稿加载失败，请检查网络后重试。'
  }
}

async function restoreAdminContextFromRoute(): Promise<void> {
  const { queueStatus: restoredQueueStatus, batchId, draftId } = getAdminRouteContext()
  queueStatus.value = restoredQueueStatus
  const batchedItems = [...groupedItems.value, ...submittedItems.value]
  if (draftId) {
    const matchedDraftItem = batchedItems.find((item) => item.draft_id === draftId)
    if (matchedDraftItem) {
      queueStatus.value = matchedDraftItem.status === 'submitted' ? 'submitted' : 'grouped'
      activeReferenceId.value = matchedDraftItem.id
      activeBatchId.value = matchedDraftItem.batch_id || batchId
      await loadDraft(draftId)
      syncAdminContextToRoute()
      return
    }
  }
  if (batchId) {
    const matchedBatchItem = batchedItems.find((item) => item.batch_id === batchId)
    if (matchedBatchItem) {
      queueStatus.value = matchedBatchItem.status === 'submitted' ? 'submitted' : 'grouped'
      activeReferenceId.value = matchedBatchItem.id
      activeBatchId.value = batchId
      if (matchedBatchItem.batch_integration_error) {
        draftMessage.value = `上次生成失败：${matchedBatchItem.batch_integration_error}。可重新生成草稿。`
      }
      syncAdminContextToRoute()
      return
    }
  }
  if (draftId || batchId) { activeReferenceId.value = ''; resetProcessingContext() }
  syncAdminContextToRoute()
}

async function integrateDraft(): Promise<void> {
  if (!activeBatchId.value) { batchMessage.value = '请先创建批次。'; return }
  integratingDraft.value = true
  draftMessage.value = ''
  try {
    const response = await apiPost<DraftIntegrateResponse, Record<string, never>>(
      buildAdminApiPath(`/draft-batches/${activeBatchId.value}/integrate`), {},
    )
    if (response.success) await loadDraft(response.data.draft_id)
    else draftMessage.value = response.message || '草稿生成失败'
  } catch {
    draftMessage.value = '草稿生成失败，请检查网络后重试。'
  } finally {
    integratingDraft.value = false
  }
}

async function saveDraft(): Promise<void> {
  if (!currentDraftId.value) { draftMessage.value = '请先生成草稿。'; return }
  savingDraft.value = true
  const payload: DraftUpdatePayload = { title: draftForm.title, body_markdown: draftForm.body_markdown }
  try {
    const response = await apiPut<{ id: string; status: string; updated_at: string }, DraftUpdatePayload>(
      buildAdminApiPath(`/drafts/${currentDraftId.value}`), payload,
    )
    if (response.success) {
      currentDraftRecord.value = {
        ...(currentDraftRecord.value || { id: currentDraftId.value, batch_id: activeBatchId.value, title: draftForm.title, body_markdown: draftForm.body_markdown, related_id_summary: draftRelatedIdSummary.value, status: response.data.status, updated_at: response.data.updated_at }),
        title: draftForm.title, body_markdown: draftForm.body_markdown,
        status: response.data.status, updated_at: response.data.updated_at,
      }
    }
    draftMessage.value = response.success ? `草稿保存成功，更新时间 ${response.data.updated_at}` : response.message || '草稿保存失败'
  } catch {
    draftMessage.value = '草稿保存失败，请检查网络后重试。'
  } finally {
    savingDraft.value = false
  }
}

async function submitDraftToGithub(): Promise<void> {
  if (!currentDraftId.value) { draftMessage.value = '请先生成草稿。'; return }
  submittingDraft.value = true
  try {
    const response = await apiPost<DraftSubmitResponse, Record<string, never>>(
      buildAdminApiPath(`/drafts/${currentDraftId.value}/submit`), {},
    )
    if (response.success) {
      submissionResult.value = response.data
      draftMessage.value = `草稿已提交，GitHub Issue #${response.data.issue_number}`
      await loadAdminData()
      await focusAdminSection('draft')
    } else {
      draftMessage.value = response.message || '提交失败'
    }
  } catch {
    draftMessage.value = '提交失败，请检查网络后重试。'
  } finally {
    submittingDraft.value = false
  }
}

function setupSectionObserver(): void {
  if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined') return
  const sections = [
    { id: 'queue-panel', section: 'queue' as const },
    { id: 'review-panel', section: 'review' as const },
    { id: 'draft-panel', section: 'draft' as const },
    { id: 'audit-panel', section: 'audit' as const },
  ]
  sectionObserver = new IntersectionObserver(
    (entries) => {
      const visibleEntry = entries.filter((entry) => entry.isIntersecting).sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0]
      if (!visibleEntry) return
      const matchedSection = sections.find((item) => item.id === visibleEntry.target.id)
      if (matchedSection) activeAdminSection.value = matchedSection.section
    },
    { threshold: [0.35, 0.55, 0.75], rootMargin: '-10% 0px -45% 0px' },
  )
  sections.forEach((item) => { const element = document.getElementById(item.id); if (element) sectionObserver?.observe(element) })
}

onMounted(async () => {
  restoreAuditFiltersFromRoute()
  restoreQueueStatusFromRoute()
  const sessionResult = await adminSessionMe()
  if (sessionResult.success && sessionResult.data.authenticated) {
    adminUsername.value = sessionResult.data.username
    isAdminUnlocked.value = true
    setAdminToken('session-active')
  } else if (hasAdminToken()) {
    clearAdminToken()
    isAdminUnlocked.value = false
  }
  if (isAdminUnlocked.value) {
    const loaded = await loadAdminData({ relockOnAuthFailure: true })
    if (!loaded) return
    await restoreAdminContextFromRoute()
    await loadAuditEvents()
    await nextTick()
    setupSectionObserver()
  }
})

onBeforeUnmount(() => {
  sectionObserver?.disconnect()
})
</script>
