<template>
  <AppShell title="Issue Triage Studio" description="整理反馈，生成 GitHub Issue 草稿。" wide>
    <section v-if="!isAdminUnlocked" class="admin-auth-screen">
      <AdminLoginCard :auth-message="adminAuthMessage" :is-logging-in="isLoggingIn" @submit="unlockAdmin" />
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
            <span>下一步</span>
            <strong>{{ nextActionTitle }}</strong>
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
              :active-item-id="activeReferenceId"
              :review-item-count="reviewItems.length"
              :current-draft-id="currentDraftId"
              @switch-queue="switchQueue"
              @toggle-selection="toggleSelection"
              @item-click="handleQueueItemClick"
              @toggle-select-all="toggleCurrentPendingSelection"
              @focus-section="focusAdminSection"
            />

            <div class="triage-workbench">
              <section class="workbench-switcher" aria-label="主工作台切换">
                <button
                  v-for="item in workbenchSections"
                  :key="item.id"
                  class="workbench-switcher__tab"
                  :class="{ 'is-active': activeWorkbenchSection === item.id }"
                  type="button"
                  @click="focusAdminSection(item.id)"
                >
                  <span>{{ item.kicker }}</span>
                  <strong>{{ item.label }}</strong>
                  <small>{{ item.hint }}</small>
                </button>
              </section>

              <ReviewPanel
                v-show="activeWorkbenchSection === 'review'"
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
                v-show="activeWorkbenchSection === 'draft'"
                :active-batch-id="activeBatchId"
                :current-draft-id="currentDraftId"
                :draft-form="{ title: draftForm.title, body_markdown: draftForm.body_markdown }"
                :submission-result="submissionResult"
                :status-label="draftStatusLabel"
                :status-description="draftStatusDescription"
                :related-id-summary="draftRelatedIdSummary"
                :updated-at-label="draftUpdatedAtLabel"
                :sync-state-label="draftSyncStateLabel"
                :sync-state-hint="draftSyncStateHint"
                :sync-state-tone="draftSyncStateTone"
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
                v-show="activeWorkbenchSection === 'audit'"
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
              />
            </div>
          </section>
        </section>

        <aside class="triage-context" aria-label="当前工作上下文">
          <section class="triage-context__panel triage-context__panel--accent triage-context__panel--dense">
            <div class="studio-section-head studio-section-head--stacked">
              <div>
                <span>Live Context</span>
                <h3>{{ contextPanelTitle }}</h3>
              </div>
              <p>{{ contextPanelDescription }}</p>
            </div>
            <div class="workflow-rail">
              <article v-for="step in workflowSteps" :key="step.index" class="workflow-step" :class="step.state">
                <span>{{ step.index }}</span>
                <strong>{{ step.label }}</strong>
              </article>
            </div>

            <section class="triage-context__priority" aria-label="当前下一步动作">
              <span>当前下一步</span>
              <strong>{{ nextActionTitle }}</strong>
              <p>{{ nextActionDescription }}</p>
            </section>

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
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
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

const statusLabelMap: Record<string, QueueStatus> & Record<string, string> = {
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
const draftSyncState = ref<
  'idle' | 'dirty' | 'generating' | 'saving' | 'saved' | 'save_error' | 'submitting' | 'submitted' | 'submit_error'
>('idle')
const draftLocalEdits = reactive<Record<string, DraftUpdatePayload>>({})
const draftLocalDirtyMap = reactive<Record<string, boolean>>({})
const queueContextMemory = reactive<
  Record<QueueStatus, { selectedIds: string[]; referenceId: string; batchId: string; draftId: string }>
>({
  pending: { selectedIds: [], referenceId: '', batchId: '', draftId: '' },
  grouped: { selectedIds: [], referenceId: '', batchId: '', draftId: '' },
  submitted: { selectedIds: [], referenceId: '', batchId: '', draftId: '' },
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

const reviewMissingCount = computed(() =>
  reviewItems.value.reduce((total, item) => total + getMissingFieldCount(item), 0),
)

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
  if (submissionResult.value)
    return `GitHub Issue #${submissionResult.value.issue_number} 已创建，可继续回看本次处理记录。`
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

const draftCanSubmit = computed(
  () => Boolean(currentDraftId.value) && Boolean(draftForm.title.trim()) && Boolean(draftForm.body_markdown.trim()),
)

const draftSyncStateLabel = computed(() => {
  if (draftSyncState.value === 'generating') return '正在生成草稿'
  if (draftSyncState.value === 'saving') return '正在保存草稿'
  if (draftSyncState.value === 'saved') return '草稿已保存'
  if (draftSyncState.value === 'save_error') return '保存失败'
  if (draftSyncState.value === 'submitting') return '正在提交 GitHub'
  if (draftSyncState.value === 'submitted') return 'GitHub 提交完成'
  if (draftSyncState.value === 'submit_error') return '提交失败'
  if (draftSyncState.value === 'dirty') return '存在未保存改动'
  if (!currentDraftId.value) return activeBatchId.value ? '等待生成草稿' : '等待创建批次'
  return '草稿上下文已就绪'
})

const draftSyncStateHint = computed(() => {
  if (draftSyncState.value === 'generating') return '系统正在把当前批次整合为结构化草稿，完成后会自动切入编辑区。'
  if (draftSyncState.value === 'saving') return '当前修改正在写回服务端，完成后会刷新最近更新时间。'
  if (draftSyncState.value === 'saved') return '草稿已经落库，可以继续编辑，也可以直接进入提交。'
  if (draftSyncState.value === 'save_error') return '保留当前输入内容，修复网络后可再次保存。'
  if (draftSyncState.value === 'submitting') return '当前草稿正在发送到 GitHub，队列与结果会在完成后同步。'
  if (draftSyncState.value === 'submitted') return '提交结果已落库，当前批次可以回看，也可以切回队列处理下一批。'
  if (draftSyncState.value === 'submit_error') return '本地草稿内容仍然保留，确认信息后可直接重试提交。'
  if (draftSyncState.value === 'dirty') return '你已经修改了标题或正文，保存后再提交可以保持批次上下文一致。'
  if (!currentDraftId.value) return activeBatchId.value ? '批次已经创建，下一步生成结构化草稿。' : '先在审阅区确认主题，再把上下文推进到草稿阶段。'
  return '当前草稿已经载入，可直接继续编辑。'
})

const draftSyncStateTone = computed<'idle' | 'active' | 'success' | 'warning'>(() => {
  if (draftSyncState.value === 'generating' || draftSyncState.value === 'saving' || draftSyncState.value === 'submitting')
    return 'active'
  if (draftSyncState.value === 'saved' || draftSyncState.value === 'submitted') return 'success'
  if (draftSyncState.value === 'dirty' || draftSyncState.value === 'save_error' || draftSyncState.value === 'submit_error')
    return 'warning'
  return 'idle'
})

const activeWorkbenchSection = computed<Exclude<AdminSection, 'queue'>>(() =>
  activeAdminSection.value === 'queue' ? 'review' : activeAdminSection.value,
)

const workbenchSections = computed(() => [
  {
    id: 'review' as const,
    kicker: '01',
    label: '聚合审阅',
    hint: reviewItems.value.length ? `${reviewItems.value.length} 条反馈待判断` : '等待从左侧队列送入',
  },
  {
    id: 'draft' as const,
    kicker: '02',
    label: '草稿与提交',
    hint: currentDraftId.value ? '草稿已生成，可直接编辑' : activeBatchId.value ? '批次已就绪，等待生稿' : '等待建批后进入',
  },
])

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
    return selectedItems.value.length
      ? '确认这些反馈是否属于同一主题，再创建批次。'
      : '从左侧队列中选择待处理反馈，这里会显示原始内容和补充信息。'
  }
  return reviewItems.value.length
    ? '这里展示当前批次中的全部反馈，便于统一回看聚合结果。'
    : '从左侧已分组或已提交队列选择一条记录，这里会显示详情。'
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
  if (activeAdminSection.value === 'draft')
    return submissionResult.value
      ? '当前批次已经提交到 GitHub，可以继续检查结果或切换到新的批次。'
      : '草稿编辑区已经接管主流程，接下来重点确认标题、正文和提交状态。'
  if (activeAdminSection.value === 'review')
    return reviewItems.value.length
      ? '当前区块用于判断这些反馈是否属于同一主题，并确定是否适合建批。'
      : '先从左侧队列中勾选或选中反馈，系统才会生成主题判断。'
  return queueStatus.value === 'pending'
    ? '优先在这里完成勾选和粗分组，避免把太多信息直接堆进后续编辑区。'
    : '当前处于历史回看模式，重点是沿着已分组或已提交链路快速回到对应草稿。'
})

const nextActionTitle = computed(() => {
  if (activeAdminSection.value === 'audit') {
    return auditEvents.value.length ? '筛选并回看目标事件' : '刷新最近审计记录'
  }
  if (activeAdminSection.value === 'draft') {
    if (submissionResult.value) return '切回队列处理下一批'
    if (currentDraftId.value) return draftCanSubmit.value ? '确认后提交 GitHub' : '继续补齐草稿内容'
    if (activeBatchId.value) return '生成当前批次草稿'
    return '先创建批次再进入编辑'
  }
  if (activeAdminSection.value === 'review') {
    if (activeBatchId.value && !currentDraftId.value) return '生成草稿进入编辑'
    if (selectedItems.value.length) return batchSummary.value.isMixed ? '拆分主题后再建批' : '确认后创建批次'
    return '先从队列选择反馈'
  }
  if (queueStatus.value === 'pending') return '勾选同主题反馈进入审阅'
  if (queueStatus.value === 'grouped') return '打开批次继续编辑草稿'
  return '回看提交记录与安全链路'
})

const nextActionDescription = computed(() => {
  if (activeAdminSection.value === 'audit') {
    return auditEvents.value.length
      ? '优先按时间、动作或资源收敛范围，快速定位异常行为和关键管理员操作。'
      : '当前列表为空，先刷新最近事件，再确认是否存在新的鉴权失败或关键操作。'
  }
  if (activeAdminSection.value === 'draft') {
    if (submissionResult.value) return '当前批次已经完成提交，主流程可以回到队列，继续处理新的主题。'
    if (currentDraftId.value) {
      return draftCanSubmit.value
        ? '标题和正文已具备提交条件，确认结构和语义后即可直接发往 GitHub。'
        : '继续补齐标题、正文和章节结构，主面板会始终保留当前批次的编辑上下文。'
    }
    if (activeBatchId.value) return '批次已经准备完成，下一步直接生成结构化草稿，避免手工从空白开始编辑。'
    return '先在审阅区确认当前主题，再建立批次，草稿区会自动接管后续流程。'
  }
  if (activeAdminSection.value === 'review') {
    if (activeBatchId.value && !currentDraftId.value) return '当前主题已经建批，进入下一步生成草稿即可开始正文整理。'
    if (selectedItems.value.length) {
      return batchSummary.value.isMixed
        ? '当前选中反馈涉及多个关联标识，先缩小范围，再建立更聚焦的批次。'
        : '当前选中反馈已经进入判断区，确认主题一致后即可把它们推进到批次。'
    }
    return '左侧队列负责提供原始反馈，先选中一组需要处理的信号，审阅区才会出现有效上下文。'
  }
  if (queueStatus.value === 'pending') return '在收件箱中勾选一组同主题反馈，系统会把它们带入审阅区继续判断。'
  if (queueStatus.value === 'grouped') return '这里适合回到已建批的历史记录，快速续写草稿或补充上下文。'
  return '当前处于已提交回看模式，重点是沿着结果记录回到对应草稿和审计链路。'
})

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

function replaceRouteQuery(entries: Record<string, string | undefined>): void {
  const nextQuery = { ...route.query }
  for (const [key, value] of Object.entries(entries)) {
    if (!value) delete nextQuery[key]
    else nextQuery[key] = value
  }
  void router.replace({ query: nextQuery })
}

function syncAdminContextToRoute(): void {
  replaceRouteQuery({
    adminQueue: queueStatus.value === 'pending' ? undefined : queueStatus.value,
    batchId: activeBatchId.value || undefined,
    draftId: currentDraftId.value || undefined,
  })
}

function syncAuditFiltersToRoute(): void {
  replaceRouteQuery({
    auditEventType: activeAuditFilter.value === 'all' ? undefined : activeAuditFilter.value,
    auditTimeRange: activeAuditTimeRange.value === 'all' ? undefined : activeAuditTimeRange.value,
    auditKeyword: auditKeyword.value || undefined,
  })
}

function syncWorkspaceStateToRoute(): void {
  replaceRouteQuery({
    adminQueue: queueStatus.value === 'pending' ? undefined : queueStatus.value,
    batchId: activeBatchId.value || undefined,
    draftId: currentDraftId.value || undefined,
    auditEventType: activeAuditFilter.value === 'all' ? undefined : activeAuditFilter.value,
    auditTimeRange: activeAuditTimeRange.value === 'all' ? undefined : activeAuditTimeRange.value,
    auditKeyword: auditKeyword.value || undefined,
  })
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
  rememberQueueContext(queueStatus.value)
  queueStatus.value = status
  activeAdminSection.value = 'queue'
  activeReferenceId.value = ''
  batchMessage.value = ''
  draftMessage.value = ''
  resetProcessingContext()
  if (status === 'pending') {
    selectedIds.value = queueContextMemory.pending.selectedIds.filter((id) => pendingItems.value.some((item) => item.id === id))
    if (selectedIds.value.length) void focusAdminSection('review')
  } else {
    selectedIds.value = []
    void restoreQueueContext(status)
  }
  syncAdminContextToRoute()
}

async function focusAdminSection(section: AdminSection): Promise<void> {
  activeAdminSection.value = section
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  await nextTick()
  const elementId =
    section === 'queue'
      ? 'queue-panel'
      : section === 'review'
        ? 'review-panel'
        : section === 'draft'
          ? 'draft-panel'
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
    rememberQueueContext(queueStatus.value)
    void loadDraft(item.draft_id)
    return
  }
  if (item.batch_integration_error) {
    draftMessage.value = `上次生成失败：${item.batch_integration_error}。可重新生成草稿。`
  }
  syncAdminContextToRoute()
  rememberQueueContext(queueStatus.value)
  void focusAdminSection('review')
}

function toggleSelection(feedbackId: string): void {
  if (!selectedIds.value.length) resetProcessingContext()
  if (selectedIds.value.includes(feedbackId)) {
    selectedIds.value = selectedIds.value.filter((id) => id !== feedbackId)
    rememberQueueContext('pending')
    return
  }
  selectedIds.value = [...selectedIds.value, feedbackId]
  rememberQueueContext('pending')
  void focusAdminSection('review')
}

function toggleCurrentPendingSelection(): void {
  if (queueStatus.value !== 'pending') return
  if (allPendingSelected.value) {
    selectedIds.value = []
    resetProcessingContext()
    rememberQueueContext('pending')
    return
  }
  resetProcessingContext()
  selectedIds.value = queueItems.value.map((item) => item.id)
  rememberQueueContext('pending')
  void focusAdminSection('review')
}

function resetDraftEditor(): void {
  currentDraftId.value = ''
  currentDraftRecord.value = null
  submissionResult.value = null
  draftSyncState.value = 'idle'
  draftForm.title = draftPreviewTitle.value
  draftForm.body_markdown = '摘要\n\n关联标识\n\n用户信号数量'
}

function isDraftDirtyAgainstRecord(record: DraftRecord | null, form: DraftUpdatePayload): boolean {
  if (!record) return false
  return record.title !== form.title || record.body_markdown !== form.body_markdown
}

function rememberQueueContext(status: QueueStatus): void {
  queueContextMemory[status] = {
    selectedIds: status === 'pending' ? [...selectedIds.value] : [],
    referenceId: activeReferenceId.value,
    batchId: activeBatchId.value,
    draftId: currentDraftId.value,
  }
}

async function restoreQueueContext(status: Exclude<QueueStatus, 'pending'>): Promise<void> {
  const memory = queueContextMemory[status]
  const items = status === 'grouped' ? groupedItems.value : submittedItems.value
  if (!items.length) return
  const matchedItem =
    items.find((item) => item.id === memory.referenceId) ||
    items.find((item) => item.draft_id === memory.draftId) ||
    items.find((item) => item.batch_id === memory.batchId)
  if (!matchedItem) return
  activeReferenceId.value = matchedItem.id
  activeBatchId.value = matchedItem.batch_id || memory.batchId
  if (matchedItem.draft_id) {
    await loadDraft(matchedItem.draft_id)
    return
  }
  if (matchedItem.batch_integration_error) {
    draftMessage.value = `上次生成失败：${matchedItem.batch_integration_error}。可重新生成草稿。`
  }
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
  queueStatus.value = 'pending'
  activeAdminSection.value = 'queue'
  activeReferenceId.value = ''
  queueContextMemory.pending = { selectedIds: [], referenceId: '', batchId: '', draftId: '' }
  queueContextMemory.grouped = { selectedIds: [], referenceId: '', batchId: '', draftId: '' }
  queueContextMemory.submitted = { selectedIds: [], referenceId: '', batchId: '', draftId: '' }
}

function clearAuditState(): void {
  auditEvents.value = []
  auditMessage.value = ''
  activeAuditFilter.value = 'all'
  activeAuditTimeRange.value = 'all'
  auditKeyword.value = ''
  auditKeywordInput.value = ''
}

function clearDraftLocalState(): void {
  Object.keys(draftLocalEdits).forEach((key) => delete draftLocalEdits[key])
  Object.keys(draftLocalDirtyMap).forEach((key) => delete draftLocalDirtyMap[key])
}

function clearAdminWorkspaceState(): void {
  clearAdminQueueState()
  clearAuditState()
  clearDraftLocalState()
  batchMessage.value = ''
  draftMessage.value = ''
  resetProcessingContext()
  syncWorkspaceStateToRoute()
}

function relockAdmin(message: string): void {
  clearAdminToken()
  isAdminUnlocked.value = false
  adminUsername.value = null
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
    throw Object.assign(new Error(response.message || 'Failed to load feedback'), {
      httpStatus: getResponseErrorStatus(response),
    })
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
    const response = await apiGet<PaginatedResponse<AuditEventRecord>>(
      buildAdminApiPath(`/audit-events?${searchParams.toString()}`),
    )
    if (response.success) {
      auditEvents.value = response.data.items
      return
    }
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

function onDraftFormUpdate(form: DraftForm): void {
  if (form.title) draftForm.title = form.title
  if (form.body_markdown) draftForm.body_markdown = form.body_markdown
  if (!currentDraftId.value) return
  draftLocalEdits[currentDraftId.value] = { title: draftForm.title, body_markdown: draftForm.body_markdown }
  const dirty = isDraftDirtyAgainstRecord(currentDraftRecord.value, draftLocalEdits[currentDraftId.value])
  draftLocalDirtyMap[currentDraftId.value] = dirty
  draftSyncState.value = dirty ? 'dirty' : 'saved'
  rememberQueueContext(queueStatus.value)
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
      const message =
        result.error_code === 'ADMIN_LOGIN_COOLDOWN_ACTIVE'
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
  } finally {
    isLoggingIn.value = false
  }
}

async function handleAdminLogout(): Promise<void> {
  try {
    await adminLogout()
  } finally {
    clearAdminToken()
    isAdminUnlocked.value = false
    adminUsername.value = null
    adminAuthMessage.value = ''
    clearAdminWorkspaceState()
  }
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
  try {
    const response = await apiPost<DraftBatchCreateResponse, DraftBatchCreatePayload>(
      buildAdminApiPath('/draft-batches'),
      payload,
    )
    if (response.success) {
      batchMessage.value = `批次创建成功：${response.data.id}`
      activeBatchId.value = response.data.id
      queueStatus.value = 'grouped'
      selectedIds.value = []
      resetDraftEditor()
      draftSyncState.value = 'idle'
      await loadAdminData()
      const firstGroupedItem = groupedItems.value.find((item) => item.batch_id === response.data.id)
      activeReferenceId.value = firstGroupedItem?.id || ''
      rememberQueueContext('grouped')
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
      const hasLocalDirtyDraft = Boolean(draftLocalDirtyMap[response.data.id] && draftLocalEdits[response.data.id])
      const draftSource = hasLocalDirtyDraft ? draftLocalEdits[response.data.id] : response.data
      draftForm.title = draftSource.title
      draftForm.body_markdown = draftSource.body_markdown
      submissionResult.value = null
      draftSyncState.value = hasLocalDirtyDraft ? 'dirty' : 'saved'
      syncAdminContextToRoute()
      rememberQueueContext(queueStatus.value)
      await focusAdminSection('draft')
      draftMessage.value = hasLocalDirtyDraft
        ? `已恢复本地未保存改动，原始更新时间 ${response.data.updated_at}`
        : `草稿已加载，更新时间 ${response.data.updated_at}`
    } else {
      draftMessage.value = response.message || '草稿加载失败'
      draftSyncState.value = 'save_error'
    }
  } catch {
    draftMessage.value = '草稿加载失败，请检查网络后重试。'
    draftSyncState.value = 'save_error'
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
      void focusAdminSection('review')
      return
    }
  }
  if (draftId || batchId) {
    activeReferenceId.value = ''
    resetProcessingContext()
  }
  syncAdminContextToRoute()
}

async function integrateDraft(): Promise<void> {
  if (!activeBatchId.value) {
    batchMessage.value = '请先创建批次。'
    return
  }
  integratingDraft.value = true
  draftMessage.value = ''
  draftSyncState.value = 'generating'
  try {
    const response = await apiPost<DraftIntegrateResponse, Record<string, never>>(
      buildAdminApiPath(`/draft-batches/${activeBatchId.value}/integrate`),
      {},
    )
    if (response.success) await loadDraft(response.data.draft_id)
    else {
      draftMessage.value = response.message || '草稿生成失败'
      draftSyncState.value = 'save_error'
    }
  } catch {
    draftMessage.value = '草稿生成失败，请检查网络后重试。'
    draftSyncState.value = 'save_error'
  } finally {
    integratingDraft.value = false
  }
}

async function saveDraft(): Promise<void> {
  if (!currentDraftId.value) {
    draftMessage.value = '请先生成草稿。'
    return
  }
  savingDraft.value = true
  draftSyncState.value = 'saving'
  const payload: DraftUpdatePayload = { title: draftForm.title, body_markdown: draftForm.body_markdown }
  try {
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
      draftLocalEdits[currentDraftId.value] = { ...payload }
      draftLocalDirtyMap[currentDraftId.value] = false
      draftSyncState.value = 'saved'
    }
    draftMessage.value = response.success
      ? ''
      : response.message || '草稿保存失败'
    if (!response.success) draftSyncState.value = 'save_error'
  } catch {
    draftMessage.value = '草稿保存失败，请检查网络后重试。'
    draftSyncState.value = 'save_error'
  } finally {
    savingDraft.value = false
  }
}

async function submitDraftToGithub(): Promise<void> {
  if (!currentDraftId.value) {
    draftMessage.value = '请先生成草稿。'
    return
  }
  submittingDraft.value = true
  draftSyncState.value = 'submitting'
  try {
    const response = await apiPost<DraftSubmitResponse, Record<string, never>>(
      buildAdminApiPath(`/drafts/${currentDraftId.value}/submit`),
      {},
    )
    if (response.success) {
      submissionResult.value = response.data
      draftLocalDirtyMap[currentDraftId.value] = false
      draftSyncState.value = 'submitted'
      draftMessage.value = `草稿已提交，GitHub Issue #${response.data.issue_number}`
      await loadAdminData()
      queueStatus.value = 'submitted'
      const matchedSubmittedItem = submittedItems.value.find((item) => item.draft_id === currentDraftId.value)
      activeReferenceId.value = matchedSubmittedItem?.id || activeReferenceId.value
      activeBatchId.value = matchedSubmittedItem?.batch_id || activeBatchId.value
      rememberQueueContext('submitted')
      syncAdminContextToRoute()
      await focusAdminSection('draft')
    } else {
      draftMessage.value = response.message || '提交失败'
      draftSyncState.value = 'submit_error'
    }
  } catch {
    draftMessage.value = '提交失败，请检查网络后重试。'
    draftSyncState.value = 'submit_error'
  } finally {
    submittingDraft.value = false
  }
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
  }
})
</script>
