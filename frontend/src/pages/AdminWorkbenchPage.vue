<template>
  <AppShell
    title="待处理反馈与草稿工作台"
    description="先聚合相近反馈，再生成、审核并提交结构化 Draft。"
  >
    <section class="content-grid content-grid--admin">
      <article class="panel panel--soft">
        <div class="panel__header">
          <h2>待处理反馈</h2>
          <p>查看待处理反馈、勾选同主题条目，并按 related_id 组织批次。</p>
        </div>
        <div class="status-bar">
          <div class="status-pill">
            <span>Pending</span>
            <strong>{{ statusCounts.pending }}</strong>
          </div>
          <div class="status-pill">
            <span>Grouped</span>
            <strong>{{ statusCounts.grouped }}</strong>
          </div>
          <div class="status-pill">
            <span>Submitted</span>
            <strong>{{ statusCounts.submitted }}</strong>
          </div>
        </div>
        <div v-if="groupedItems.length" class="grouped-panel">
          <h3>已建批次反馈</h3>
          <div class="stack-list">
            <button
              v-for="item in groupedItems"
              :key="item.id"
              class="list-button"
              type="button"
              @click="selectGroupedRelatedId(item.related_id)"
            >
              <span class="tag">{{ item.type }}</span>
              <strong>{{ item.related_id }}</strong>
              <span>{{ item.raw_content }}</span>
            </button>
          </div>
        </div>
        <div class="table-shell">
          <div class="table-row table-row--head">
            <span>选择</span>
            <span>类型</span>
            <span>Related ID</span>
            <span>摘要</span>
          </div>
          <div v-for="item in pendingItems" :key="item.id" class="table-row">
            <span><input :checked="selectedIds.includes(item.id)" type="checkbox" @change="toggleSelection(item.id)" /></span>
            <span>{{ item.type }}</span>
            <span>{{ item.related_id }}</span>
            <span>{{ item.raw_content }}</span>
          </div>
          <div v-if="!pendingItems.length && !loading" class="empty-state table-empty">当前没有待处理反馈。</div>
          <div v-if="loading" class="empty-state table-empty">正在加载反馈列表...</div>
        </div>
      </article>

      <article class="panel">
        <div class="panel__header">
          <h2>批次与 Draft</h2>
          <p>按批次生成 Draft，补全缺失信息后保存，下一步再接 GitHub 提交。</p>
        </div>
        <div class="two-column-panels">
          <section class="subpanel">
            <h3>批次摘要</h3>
            <ul class="key-list">
              <li>主 related_id：{{ batchSummary.primaryRelatedId || '待选择' }}</li>
              <li>涉及条目：{{ batchSummary.itemCount }}</li>
              <li>混合 related_id：{{ batchSummary.isMixed ? '是' : '否' }}</li>
              <li>当前批次：{{ activeBatchId || '尚未创建' }}</li>
            </ul>
            <div v-if="batchMessage" class="feedback-message">{{ batchMessage }}</div>
            <div class="actions-row">
              <button class="button button--secondary" type="button" @click="createBatch">
              {{ creatingBatch ? '创建中...' : batchSummary.isMixed ? '确认并创建批次' : '创建批次' }}
              </button>
              <button class="button" type="button" :disabled="!activeBatchId || integratingDraft" @click="integrateDraft">
                {{ integratingDraft ? '生成中...' : '生成 Draft' }}
              </button>
            </div>
          </section>
          <section class="subpanel">
            <h3>Draft 编辑器</h3>
            <input v-model="draftForm.title" class="input" :readonly="!currentDraftId" />
            <textarea v-model="draftForm.body_markdown" class="textarea" rows="16" :readonly="!currentDraftId"></textarea>
            <div v-if="draftMessage" class="feedback-message">{{ draftMessage }}</div>
            <div v-if="submissionResult" class="warning-box">
              <strong>GitHub 提交结果</strong>
              <p>
                已提交为
                <a :href="submissionResult.issue_url" target="_blank" rel="noreferrer">
                  #{{ submissionResult.issue_number }}
                </a>
                ，时间 {{ submissionResult.submitted_at }}
              </p>
            </div>
            <div class="actions-row">
              <button class="button button--secondary" type="button" :disabled="!currentDraftId || savingDraft" @click="saveDraft">
                {{ savingDraft ? '保存中...' : '保存 Draft' }}
              </button>
              <button class="button" type="button" :disabled="!currentDraftId || submittingDraft" @click="submitDraftToGithub">
                {{ submittingDraft ? '提交中...' : '提交到 GitHub' }}
              </button>
            </div>
          </section>
        </div>
      </article>
    </section>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '../components/layout/AppShell.vue'
import {
  apiGet,
  apiPost,
  apiPut,
  type DraftBatchCreatePayload,
  type DraftBatchCreateResponse,
  type DraftIntegrateResponse,
  type DraftRecord,
  type DraftSubmitResponse,
  type DraftUpdatePayload,
  type FeedbackItem,
  type PaginatedResponse,
} from '../services/api'

const pendingItems = ref<FeedbackItem[]>([])
const groupedItems = ref<FeedbackItem[]>([])
const submittedItems = ref<FeedbackItem[]>([])
const selectedIds = ref<string[]>([])
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

const draftForm = reactive<DraftUpdatePayload>({
  title: '[Draft] 请选择反馈后生成标题',
  body_markdown: 'Summary\n\nRelated ID\n\nUser Signals Count',
})

const statusCounts = computed(() => ({
  pending: pendingItems.value.length,
  grouped: groupedItems.value.length,
  submitted: submittedItems.value.length,
}))

const selectedItems = computed(() => pendingItems.value.filter((item) => selectedIds.value.includes(item.id)))

const batchSummary = computed(() => {
  const relatedIds = [...new Set(selectedItems.value.map((item) => item.related_id))]
  return {
    primaryRelatedId: relatedIds.length === 1 ? relatedIds[0] : null,
    itemCount: selectedItems.value.length,
    isMixed: relatedIds.length > 1,
  }
})

const draftPreviewTitle = computed(() => {
  if (currentDraftId.value) {
    return draftForm.title
  }
  if (!selectedItems.value.length) {
    return '[Draft] 请选择反馈后生成标题'
  }
  if (batchSummary.value.primaryRelatedId) {
    return `[Draft] ${batchSummary.value.primaryRelatedId}`
  }
  return '[Draft] Mixed related_id batch'
})

function toggleSelection(feedbackId: string): void {
  batchMessage.value = ''
  draftMessage.value = ''
  if (selectedIds.value.includes(feedbackId)) {
    selectedIds.value = selectedIds.value.filter((id) => id !== feedbackId)
    return
  }
  selectedIds.value = [...selectedIds.value, feedbackId]
}

function resetDraftEditor(): void {
  currentDraftId.value = ''
  submissionResult.value = null
  draftForm.title = draftPreviewTitle.value
  draftForm.body_markdown = 'Summary\n\nRelated ID\n\nUser Signals Count'
}

function selectGroupedRelatedId(relatedId: string): void {
  const matchingItems = groupedItems.value.filter((item) => item.related_id === relatedId)
  batchMessage.value = `已定位 grouped 反馈：${relatedId}，请先生成对应 Draft。`
  selectedIds.value = matchingItems.map((item) => item.id)
}

async function loadFeedbackByStatus(status: string): Promise<FeedbackItem[]> {
  const response = await apiGet<PaginatedResponse<FeedbackItem>>(`/api/feedback?status=${status}`)
  return response.success ? response.data.items : []
}

async function loadAdminData(): Promise<void> {
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
  loading.value = false
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
  const response = await apiPost<DraftBatchCreateResponse, DraftBatchCreatePayload>('/api/draft-batches', payload)

  if (response.success) {
    batchMessage.value = `批次创建成功：${response.data.id}`
    activeBatchId.value = response.data.id
    selectedIds.value = []
    resetDraftEditor()
    await loadAdminData()
  } else {
    batchMessage.value = response.message || '批次创建失败'
  }

  creatingBatch.value = false
}

async function loadDraft(draftId: string): Promise<void> {
  const response = await apiGet<DraftRecord>(`/api/drafts/${draftId}`)
  if (response.success) {
    currentDraftId.value = response.data.id
    draftForm.title = response.data.title
    draftForm.body_markdown = response.data.body_markdown
    submissionResult.value = null
    draftMessage.value = `Draft 已加载，更新时间 ${response.data.updated_at}`
  } else {
    draftMessage.value = response.message || 'Draft 加载失败'
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
    `/api/draft-batches/${activeBatchId.value}/integrate`,
    {},
  )

  if (response.success) {
    await loadDraft(response.data.draft_id)
  } else {
    draftMessage.value = response.message || 'Draft 生成失败'
  }

  integratingDraft.value = false
}

async function saveDraft(): Promise<void> {
  if (!currentDraftId.value) {
    draftMessage.value = '请先生成 Draft。'
    return
  }

  savingDraft.value = true
  const payload: DraftUpdatePayload = {
    title: draftForm.title,
    body_markdown: draftForm.body_markdown,
  }
  const response = await apiPut<{ id: string; status: string; updated_at: string }, DraftUpdatePayload>(
    `/api/drafts/${currentDraftId.value}`,
    payload,
  )

  draftMessage.value = response.success
    ? `Draft 保存成功，更新时间 ${response.data.updated_at}`
    : response.message || 'Draft 保存失败'
  savingDraft.value = false
}

async function submitDraftToGithub(): Promise<void> {
  if (!currentDraftId.value) {
    draftMessage.value = '请先生成 Draft。'
    return
  }

  submittingDraft.value = true
  const response = await apiPost<DraftSubmitResponse, Record<string, never>>(
    `/api/drafts/${currentDraftId.value}/submit`,
    {},
  )

  if (response.success) {
    submissionResult.value = response.data
    draftMessage.value = `Draft 已提交，Issue #${response.data.issue_number}`
    await loadAdminData()
  } else {
    draftMessage.value = response.message || '提交失败'
  }

  submittingDraft.value = false
}

onMounted(async () => {
  await loadAdminData()
})
</script>
