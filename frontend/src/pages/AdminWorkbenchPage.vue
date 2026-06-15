<template>
  <AppShell
    title="Issue Triage Studio"
    description="整理反馈，生成 GitHub Issue 草稿。"
    wide
  >
    <section v-if="!isAdminUnlocked" class="admin-auth-screen">
      <form class="admin-auth-card" @submit.prevent="unlockAdmin">
        <p class="eyebrow">Restricted Area</p>
        <h2>管理员登录</h2>
        <p>输入账号密码后加载队列和草稿。</p>
        <label class="field field--full">
          <span>用户名</span>
          <input v-model="adminUsernameInput" class="input" type="text" autocomplete="username" placeholder="admin" />
        </label>
        <label class="field field--full">
          <span>密码</span>
          <input v-model="adminPasswordInput" class="input" type="password" autocomplete="current-password" placeholder="********" />
        </label>
        <div v-if="adminAuthMessage" class="feedback-message feedback-message--error">{{ adminAuthMessage }}</div>
        <button class="button" type="submit" :disabled="isLoggingIn">{{ isLoggingIn ? '登录中…' : '登录' }}</button>
      </form>
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
        <aside class="triage-sidebar" aria-label="管理工作区导航">
          <section class="triage-sidebar__panel">
            <div class="studio-section-head studio-section-head--stacked">
              <div>
                <span>Queue Switch</span>
                <h3>处理队列</h3>
              </div>
              <p>先切换到当前要处理的队列，再进入对应工作步骤。</p>
            </div>
            <div class="triage-sidebar__status-list" aria-label="反馈状态统计">
              <button class="triage-tab triage-tab--sidebar" :class="{ 'is-active': queueStatus === 'pending' }" type="button" @click="switchQueue('pending')">
                <span>待整理</span>
                <strong>{{ statusCounts.pending }}</strong>
              </button>
              <button class="triage-tab triage-tab--sidebar" :class="{ 'is-active': queueStatus === 'grouped' }" type="button" @click="switchQueue('grouped')">
                <span>草稿中</span>
                <strong>{{ statusCounts.grouped }}</strong>
              </button>
              <button class="triage-tab triage-tab--sidebar" :class="{ 'is-active': queueStatus === 'submitted' }" type="button" @click="switchQueue('submitted')">
                <span>已发布</span>
                <strong>{{ statusCounts.submitted }}</strong>
              </button>
            </div>
          </section>

          <section class="triage-sidebar__panel">
            <div class="studio-section-head studio-section-head--stacked">
              <div>
                <span>Studio Nav</span>
                <h3>工作步骤</h3>
              </div>
              <p>按照队列、审阅、草稿、审计的顺序推进当前处理链路。</p>
            </div>
            <div class="triage-sidebar__nav-list">
              <button class="triage-nav-card" :class="{ 'is-active': activeAdminSection === 'queue' }" type="button" @click="focusAdminSection('queue')">
                <div>
                  <span>01</span>
                  <strong>反馈队列</strong>
                </div>
                <small>{{ queueItems.length }} 条</small>
              </button>
              <button class="triage-nav-card" :class="{ 'is-active': activeAdminSection === 'review' }" type="button" @click="focusAdminSection('review')">
                <div>
                  <span>02</span>
                  <strong>主题判断</strong>
                </div>
                <small>{{ reviewItems.length }} 条</small>
              </button>
              <button class="triage-nav-card" :class="{ 'is-active': activeAdminSection === 'draft' }" type="button" @click="focusAdminSection('draft')">
                <div>
                  <span>03</span>
                  <strong>草稿编辑</strong>
                </div>
                <small>{{ currentDraftId ? '可提交' : '待生成' }}</small>
              </button>
              <button class="triage-nav-card" :class="{ 'is-active': activeAdminSection === 'audit' }" type="button" @click="focusAdminSection('audit')">
                <div>
                  <span>04</span>
                  <strong>审计记录</strong>
                </div>
                <small>{{ auditEvents.length }} 条</small>
              </button>
            </div>
          </section>
        </aside>

        <section class="triage-main">
          <section class="triage-grid">
        <article id="queue-panel" class="signal-stream">
          <header class="studio-section-head">
            <div>
              <span>Signal Stream</span>
              <h3>{{ queueHeading }}</h3>
            </div>
            <p>{{ queueDescription }}</p>
          </header>

          <div class="queue-overview">
            <strong>{{ statusCounts[queueStatus] }}</strong>
            <span>{{ queueStatus === 'pending' ? '等待进入本轮整理的反馈' : queueStatus === 'grouped' ? '已进入批次、可继续整理的反馈' : '已经完成提交的反馈记录' }}</span>
          </div>

          <div v-if="queueStatus === 'pending' && queueItems.length" class="signal-actions">
            <button class="button button--quiet button--compact" type="button" @click="toggleCurrentPendingSelection">
              {{ allPendingSelected ? '取消全选' : '一键勾选' }}
            </button>
            <span>已选 {{ selectedIds.length }} / {{ queueItems.length }}</span>
          </div>

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
            <div v-if="!queueItems.length && !loading" class="empty-state">
              <strong class="empty-state__title">当前队列为空</strong>
              <span class="empty-state__hint">切换到其他状态，或等待新的反馈进入这个阶段。</span>
            </div>
            <div v-if="loading" class="empty-state empty-state--loading">正在载入...</div>
          </div>
        </article>

        <div class="triage-workbench">
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
                <section class="evidence-card__summary">
                  <span>反馈摘要</span>
                  <p>{{ item.raw_content }}</p>
                </section>
                <dl class="evidence-card__compare">
                  <div class="evidence-card__compare-block">
                    <dt>期望</dt>
                    <dd>{{ item.expected_behavior || '待补充' }}</dd>
                  </div>
                  <div class="evidence-card__compare-block">
                    <dt>实际</dt>
                    <dd>{{ item.actual_behavior || '待补充' }}</dd>
                  </div>
                </dl>
              </article>
              <div v-if="!reviewItems.length" class="empty-state">
                <strong class="empty-state__title">等待生成主题画布</strong>
                <span class="empty-state__hint">先在左侧选择反馈，这里会汇总主题、缺失信息和聚合判断。</span>
              </div>
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

            <div class="issue-editor__meta issue-editor__meta--badges">
              <span>{{ draftRelatedIdSummary }}</span>
              <span>{{ activeBatchId || '待建批' }}</span>
              <span>{{ draftUpdatedAtLabel }}</span>
            </div>

            <section class="batch-insight-grid" aria-label="批次摘要信息">
              <article class="batch-insight-card">
                <span>批次条目数</span>
                <strong>{{ reviewItems.length }}</strong>
              </article>
              <article class="batch-insight-card">
                <span>关联标识数</span>
                <strong>{{ activeReviewRelatedIds.length || batchSummary.relatedIdCount || 0 }}</strong>
              </article>
              <article class="batch-insight-card">
                <span>最近保存</span>
                <strong>{{ draftUpdatedAtLabel }}</strong>
              </article>
            </section>

            <div class="draft-editor-note">
              <strong>{{ draftEditorHeadline }}</strong>
              <p>{{ draftEditorHint }}</p>
            </div>

            <label class="field field--full issue-title-field">
              <span>Issue 标题</span>
              <small class="field-helper">标题保持聚焦，优先写清问题对象和结果。</small>
              <input v-model="draftForm.title" class="input" :readonly="!currentDraftId" />
            </label>
            <label class="field field--full issue-body-field">
              <span>Issue 正文</span>
              <small class="field-helper">正文按摘要、背景、期望、实际和影响展开，便于直接提交到 GitHub。</small>
              <textarea v-model="draftForm.body_markdown" class="textarea textarea--editor" rows="18" :readonly="!currentDraftId"></textarea>
            </label>

            <div v-if="draftMessage" class="feedback-message draft-message">{{ draftMessage }}</div>
            <section v-if="showDraftSubmissionChecklist" class="submission-readiness-card" aria-label="提交前确认信息">
              <strong>提交前确认</strong>
              <p>{{ draftSubmissionChecklistSummary }}</p>
              <div class="submission-readiness-card__facts">
                <span>标题 {{ draftTitleLength }} 字</span>
                <span>正文 {{ draftBodyLength }} 字</span>
                <span>{{ draftSectionCount }} 个 Markdown 小节</span>
              </div>
            </section>
            <div v-if="submissionResult" class="warning-box submission-card submission-card--result">
              <strong>GitHub Issue #{{ submissionResult.issue_number }}</strong>
              <p>
                已提交到
                <a :href="submissionResult.issue_url" target="_blank" rel="noreferrer">GitHub</a>
                ，时间 {{ submissionResult.submitted_at }}
              </p>
            </div>

            <div class="studio-actions issue-actions issue-actions--dock">
              <button class="button button--secondary" type="button" :disabled="!activeBatchId || integratingDraft" @click="integrateDraft">
                {{ integratingDraft ? '生成中...' : '生成草稿' }}
              </button>
              <button class="button button--quiet" type="button" :disabled="!currentDraftId || savingDraft" @click="saveDraft">
                {{ savingDraft ? '保存中...' : '保存草稿' }}
              </button>
              <button class="button" type="button" :disabled="!draftCanSubmit || submittingDraft" @click="submitDraftToGithub">
                {{ submittingDraft ? '提交中...' : '提交 GitHub' }}
              </button>
            </div>
          </article>

          <section id="audit-panel" class="audit-stream audit-stream--secondary">
            <header class="studio-section-head">
              <div>
                <span>Security Events</span>
                <h3>最近审计事件</h3>
              </div>
              <p>查看最近的管理员鉴权失败和成功操作，便于快速回看安全链路。</p>
            </header>

            <div class="audit-stream__meta">
              <span>最近 {{ auditEvents.length }} 条</span>
              <button class="button button--quiet button--compact" type="button" :disabled="loadingAuditEvents" @click="loadAuditEvents">
                {{ loadingAuditEvents ? '刷新中...' : '刷新事件' }}
              </button>
            </div>

            <div class="audit-filters">
              <button
                v-for="option in auditFilterOptions"
                :key="option.value"
                class="audit-filter-chip"
                :class="{ 'is-active': activeAuditFilter === option.value }"
                type="button"
                :disabled="loadingAuditEvents"
                @click="applyAuditFilter(option.value)"
              >
                {{ option.label }}
              </button>
            </div>

            <div class="audit-filters audit-filters--time">
              <button
                v-for="option in auditTimeRangeOptions"
                :key="option.value"
                class="audit-filter-chip"
                :class="{ 'is-active': activeAuditTimeRange === option.value }"
                type="button"
                :disabled="loadingAuditEvents"
                @click="applyAuditTimeRange(option.value)"
              >
                {{ option.label }}
              </button>
            </div>

            <div class="audit-search">
              <input
                v-model="auditKeywordInput"
                class="input"
                type="text"
                placeholder="按 IP、路径、动作或资源检索"
                :disabled="loadingAuditEvents"
                @keydown.enter.prevent="applyAuditKeyword"
              />
              <button class="button button--quiet button--compact" type="button" :disabled="loadingAuditEvents" @click="applyAuditKeyword">
                检索
              </button>
            </div>

            <div v-if="auditMessage" class="feedback-message feedback-message--subtle">{{ auditMessage }}</div>
            <div class="audit-list">
              <article v-for="event in auditEvents" :key="event.id" class="audit-card">
                <div class="audit-card__meta">
                  <strong>{{ getAuditEventLabel(event) }}</strong>
                  <span>{{ describeAuditEventTime(event.created_at) }}</span>
                </div>
                <p>{{ describeAuditEvent(event) }}</p>
                <div class="audit-card__tags">
                  <span>{{ event.client_ip }}</span>
                  <span>{{ event.path }}</span>
                  <span v-if="event.resource_id">{{ event.resource_id }}</span>
                </div>
              </article>
              <div v-if="!auditEvents.length && !loadingAuditEvents" class="empty-state">
                <strong class="empty-state__title">暂无审计事件</strong>
                <span class="empty-state__hint">当管理员鉴权失败或完成关键操作后，这里会记录最近的安全链路。</span>
              </div>
            </div>
          </section>
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
import {
  adminLogin,
  adminLogout,
  adminSessionMe,
  apiGet,
  apiPost,
  apiPut,
  buildAdminApiPath,
  buildSubmittedIssueSearch,
  clearAdminToken,
  hasAdminToken,
  setAdminToken,
  type AdminSessionStatus,
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

type QueueStatus = 'pending' | 'grouped' | 'submitted'
type AdminSection = 'queue' | 'review' | 'draft' | 'audit'
type AuditEventFilter = 'all' | 'admin_auth_failed' | 'admin_action_succeeded'
type AuditTimeRange = 'all' | '10m' | '1h' | '24h'
type AdminRouteContext = {
  queueStatus: QueueStatus
  batchId: string
  draftId: string
}

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

const activeBatchItems = computed(() => {
  if (!activeBatchId.value) {
    return [] as FeedbackItem[]
  }
  return queueItems.value.filter((item) => item.batch_id === activeBatchId.value)
})

const allPendingSelected = computed(() => {
  if (queueStatus.value !== 'pending' || !queueItems.value.length) {
    return false
  }
  return queueItems.value.every((item) => selectedIds.value.includes(item.id))
})

const reviewItems = computed(() => {
  if (queueStatus.value === 'pending') {
    return selectedItems.value
  }
  if (activeBatchItems.value.length) {
    return activeBatchItems.value
  }
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
  if (activeReviewRelatedIds.value.length === 1) {
    return activeReviewRelatedIds.value[0]
  }
  return activeReferenceItem.value?.related_id || ''
})

const reviewMissingCount = computed(() => reviewItems.value.reduce((total, item) => total + getMissingFieldCount(item), 0))

const reviewCanCreateBatch = computed(() => {
  if (queueStatus.value !== 'pending') {
    return Boolean(activeReferenceItem.value)
  }
  return selectedItems.value.length > 0
})

const reviewDecisionTitle = computed(() => {
  if (queueStatus.value !== 'pending') {
    return reviewItems.value.length ? '当前批次可作为回看参考' : '等待选择参考记录'
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
    return reviewItems.value.length
      ? `当前批次共包含 ${reviewItems.value.length} 条反馈，可直接回看聚合结果与草稿上下文。`
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

const draftEditorHeadline = computed(() => {
  if (submissionResult.value) {
    return 'GitHub 提交已完成'
  }
  if (!activeBatchId.value) {
    return '等待进入草稿阶段'
  }
  if (!currentDraftId.value) {
    return '先生成草稿，再进入编辑'
  }
  return '当前草稿可直接继续完善'
})

const draftEditorHint = computed(() => {
  if (submissionResult.value) {
    return '当前版本已经提交成功，可以继续回看正文结构或切换到其他批次。'
  }
  if (!activeBatchId.value) {
    return '左侧完成建批后，这里会出现标题、正文和提交动作。'
  }
  if (!currentDraftId.value) {
    return '生成后的草稿会自动带入批次上下文，便于你继续整理 Markdown 内容。'
  }
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
  if (!currentDraftId.value) {
    return '生成草稿后，这里会显示提交前需要确认的关键信息。'
  }

  return `当前草稿关联 ${draftRelatedIdSummary.value}，覆盖 ${reviewItems.value.length} 条反馈。保存后可直接提交到 GitHub。`
})

const draftCanSubmit = computed(() => Boolean(currentDraftId.value) && Boolean(draftForm.title.trim()) && Boolean(draftForm.body_markdown.trim()))

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
  if (activeAdminSection.value === 'audit') {
    return '审计与安全'
  }
  if (activeAdminSection.value === 'review') {
    return '聚合审阅'
  }
  if (activeAdminSection.value === 'draft') {
    return '草稿与提交'
  }
  return '反馈队列'
})

const contextPrimaryRelatedId = computed(() => {
  if (draftRelatedIdSummary.value && draftRelatedIdSummary.value !== '待确认') {
    return draftRelatedIdSummary.value
  }
  if (batchSummary.value.primaryRelatedId) {
    return batchSummary.value.primaryRelatedId
  }
  if (activeReferenceRelatedId.value) {
    return activeReferenceRelatedId.value
  }
  return '待确认'
})

const contextPanelTitle = computed(() => {
  if (activeAdminSection.value === 'audit') {
    return '回看安全链路'
  }
  if (activeAdminSection.value === 'draft') {
    return submissionResult.value ? '已完成提交' : '准备编辑与提交'
  }
  if (activeAdminSection.value === 'review') {
    return reviewItems.value.length ? '当前主题判断中' : '等待进入主题判断'
  }
  return queueStatus.value === 'pending' ? '待整理反馈收件箱' : '历史批次回看模式'
})

const contextPanelDescription = computed(() => {
  if (activeAdminSection.value === 'audit') {
    return '这里主要用于确认管理员操作是否完整落库，以及近期是否存在异常鉴权。'
  }
  if (activeAdminSection.value === 'draft') {
    return submissionResult.value
      ? '当前批次已经提交到 GitHub，可以继续检查结果或切换到新的批次。'
      : '草稿编辑区已经接管主流程，接下来重点确认标题、正文和提交状态。'
  }
  if (activeAdminSection.value === 'review') {
    return reviewItems.value.length
      ? '当前区块用于判断这些反馈是否属于同一主题，并确定是否适合建批。'
      : '先从左侧队列中勾选或选中反馈，系统才会生成主题判断。'
  }
  return queueStatus.value === 'pending'
    ? '优先在这里完成勾选和粗分组，避免把太多信息直接堆进后续编辑区。'
    : '当前处于历史回看模式，重点是沿着已分组或已提交链路快速回到对应草稿。'
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

function getAuditEventLabel(event: AuditEventRecord): string {
  if (event.event_type === 'admin_auth_failed') {
    return '管理员鉴权失败'
  }
  return event.action ? `管理员操作成功 · ${event.action}` : '管理员操作成功'
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

function getAdminRouteContext(): AdminRouteContext {
  return {
    queueStatus: parseQueueStatus(route.query.adminQueue),
    batchId: parseContextId(route.query.batchId),
    draftId: parseContextId(route.query.draftId),
  }
}

function syncAdminContextToRoute(): void {
  const nextQuery = { ...route.query }
  if (queueStatus.value === 'pending') {
    delete nextQuery.adminQueue
  } else {
    nextQuery.adminQueue = queueStatus.value
  }

  if (!activeBatchId.value) {
    delete nextQuery.batchId
  } else {
    nextQuery.batchId = activeBatchId.value
  }

  if (!currentDraftId.value) {
    delete nextQuery.draftId
  } else {
    nextQuery.draftId = currentDraftId.value
  }

  void router.replace({ query: nextQuery })
}

function syncAuditFiltersToRoute(): void {
  const nextQuery = { ...route.query }
  if (activeAuditFilter.value === 'all') {
    delete nextQuery.auditEventType
  } else {
    nextQuery.auditEventType = activeAuditFilter.value
  }

  if (activeAuditTimeRange.value === 'all') {
    delete nextQuery.auditTimeRange
  } else {
    nextQuery.auditTimeRange = activeAuditTimeRange.value
  }

  if (!auditKeyword.value) {
    delete nextQuery.auditKeyword
  } else {
    nextQuery.auditKeyword = auditKeyword.value
  }

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

function describeAuditEventTime(value: string): string {
  const timestamp = toComparableDate(value)
  if (!timestamp) {
    return formatTimestamp(value)
  }
  return timestamp.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function describeAuditEvent(event: AuditEventRecord): string {
  if (event.event_type === 'admin_auth_failed') {
    return `管理接口 ${event.path} 出现一次鉴权失败请求。`
  }
  if (event.action && event.resource_id) {
    return `管理员完成 ${event.action}，关联资源 ${event.resource_id}。`
  }
  if (event.action) {
    return `管理员完成 ${event.action}。`
  }
  return `管理员请求 ${event.path} 执行成功。`
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
  syncAdminContextToRoute()
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

  const elementId = section === 'queue'
    ? 'queue-panel'
    : section === 'review'
      ? 'review-panel'
      : section === 'draft'
        ? 'draft-panel'
        : 'audit-panel'
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

function toggleCurrentPendingSelection(): void {
  if (queueStatus.value !== 'pending') {
    return
  }

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

function getResponseErrorStatus(response: ApiEnvelope<unknown>): number | undefined {
  return response.success ? undefined : response.http_status
}

function getErrorHttpStatus(error: unknown): number | undefined {
  if (typeof error !== 'object' || !error || !('httpStatus' in error)) {
    return undefined
  }
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
  if (!isAdminUnlocked.value) {
    return
  }

  loadingAuditEvents.value = true
  auditMessage.value = ''
  try {
    const searchParams = new URLSearchParams({ page_size: '8' })
    if (activeAuditFilter.value !== 'all') {
      searchParams.set('event_type', activeAuditFilter.value)
    }
    if (activeAuditTimeRange.value !== 'all') {
      searchParams.set('time_range', activeAuditTimeRange.value)
    }
    if (auditKeyword.value) {
      searchParams.set('keyword', auditKeyword.value)
    }
    const response = await apiGet<PaginatedResponse<AuditEventRecord>>(buildAdminApiPath(`/audit-events?${searchParams.toString()}`))
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
  if (activeAuditFilter.value === filter) {
    return
  }
  activeAuditFilter.value = filter
  syncAuditFiltersToRoute()
  await loadAuditEvents()
}

async function applyAuditTimeRange(timeRange: AuditTimeRange): Promise<void> {
  if (activeAuditTimeRange.value === timeRange) {
    return
  }
  activeAuditTimeRange.value = timeRange
  syncAuditFiltersToRoute()
  await loadAuditEvents()
}

async function applyAuditKeyword(): Promise<void> {
  auditKeyword.value = auditKeywordInput.value.trim()
  syncAuditFiltersToRoute()
  await loadAuditEvents()
}

async function loadAdminData(options: { relockOnAuthFailure?: boolean } = {}): Promise<boolean> {
  if (!isAdminUnlocked.value) {
    return false
  }
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

async function unlockAdmin(): Promise<void> {
  const username = adminUsernameInput.value.trim()
  const password = adminPasswordInput.value
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
    adminPasswordInput.value = ''
    isAdminUnlocked.value = true
    setAdminToken('session-active')
    const loaded = await loadAdminData({ relockOnAuthFailure: true })
    if (!loaded) {
      return
    }
    await loadAuditEvents()
    await nextTick()
    setupSectionObserver()
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
  try {
    const response = await apiPost<DraftIntegrateResponse, Record<string, never>>(
      buildAdminApiPath(`/draft-batches/${activeBatchId.value}/integrate`),
      {},
    )

    if (response.success) {
      await loadDraft(response.data.draft_id)
    } else {
      draftMessage.value = response.message || '草稿生成失败'
    }
  } catch {
    draftMessage.value = '草稿生成失败，请检查网络后重试。'
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
  const payload: DraftUpdatePayload = {
    title: draftForm.title,
    body_markdown: draftForm.body_markdown,
  }
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
    }

    draftMessage.value = response.success
      ? `草稿保存成功，更新时间 ${response.data.updated_at}`
      : response.message || '草稿保存失败'
  } catch {
    draftMessage.value = '草稿保存失败，请检查网络后重试。'
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
  try {
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
  } catch {
    draftMessage.value = '提交失败，请检查网络后重试。'
  } finally {
    submittingDraft.value = false
  }
}

function setupSectionObserver(): void {
  if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined') {
    return
  }

  const sections = [
    { id: 'queue-panel', section: 'queue' as const },
    { id: 'review-panel', section: 'review' as const },
    { id: 'draft-panel', section: 'draft' as const },
    { id: 'audit-panel', section: 'audit' as const },
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
    if (!loaded) {
      return
    }
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
