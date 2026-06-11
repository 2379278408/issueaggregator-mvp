<template>
  <AppShell
    title="提交反馈前，先检查是否已有相关 Issue"
    description="先看历史，再补充新信息，能让后续整理和提交更快。"
  >
    <section class="content-grid content-grid--user">
      <article class="panel panel--soft">
        <div class="panel__header">
          <h2>已提交 Issue</h2>
          <p>按 related_id、类型和关键词检查历史提交，减少重复反馈。</p>
        </div>
        <div class="toolbar-row">
          <input v-model="filters.keyword" class="input" placeholder="搜索 related_id 或关键词" />
          <select v-model="filters.type" class="select">
            <option value="all">全部类型</option>
            <option value="bug">bug</option>
            <option value="feature">feature</option>
            <option value="enhancement">enhancement</option>
            <option value="question">question</option>
          </select>
          <button class="button button--secondary" type="button" @click="loadSubmittedIssues">搜索</button>
        </div>
        <div class="stack-list">
          <article v-for="issue in submittedIssues" :key="issue.issue_number" class="issue-card">
            <div class="issue-card__meta">
              <span class="tag">{{ issue.type }}</span>
              <span>#{{ issue.issue_number }}</span>
              <span>{{ issue.related_id }}</span>
            </div>
            <h3>
              <a :href="issue.issue_url" target="_blank" rel="noreferrer">{{ issue.title }}</a>
            </h3>
            <p>提交时间：{{ issue.submitted_at }}</p>
          </article>
          <div v-if="!submittedIssues.length && !issuesLoading" class="empty-state">当前还没有已提交 Issue。</div>
          <div v-if="issuesLoading" class="empty-state">正在加载已提交 Issue...</div>
        </div>
      </article>

      <article class="panel">
        <div class="panel__header">
          <h2>反馈表单</h2>
          <p>提交时必须填写稳定的 related_id。</p>
        </div>
        <div class="warning-box">
          <strong>{{ duplicateIssues.length ? '检测到相同 related_id 的历史 Issue' : 'Related ID 提示区' }}</strong>
          <p v-if="duplicateIssues.length">当前 related_id 已存在 {{ duplicateIssues.length }} 条历史 Issue，请优先补充新增信息。</p>
          <p v-else>输入 related_id 后，这里会显示同主题的历史 Issue。</p>
          <ul v-if="duplicateIssues.length" class="duplicate-list">
            <li v-for="issue in duplicateIssues" :key="issue.issue_number">
              <a :href="issue.issue_url" target="_blank" rel="noreferrer">#{{ issue.issue_number }} {{ issue.title }}</a>
            </li>
          </ul>
        </div>
        <form class="form-grid" @submit.prevent="submitFeedback">
          <label class="field">
            <span>反馈类型</span>
            <select v-model="form.type" class="select">
              <option value="bug">bug</option>
              <option value="feature">feature</option>
              <option value="enhancement">enhancement</option>
              <option value="question">question</option>
            </select>
          </label>
          <label class="field">
            <span>Related ID</span>
            <input v-model="form.related_id" class="input" placeholder="editor-copy-button" @blur="loadDuplicateIssues" />
          </label>
          <label class="field field--full">
            <span>反馈内容</span>
            <textarea v-model="form.raw_content" class="textarea" rows="6" placeholder="描述现象、场景和影响"></textarea>
          </label>
          <label class="field">
            <span>期望行为</span>
            <textarea v-model="form.expected_behavior" class="textarea" rows="3"></textarea>
          </label>
          <label class="field">
            <span>实际行为</span>
            <textarea v-model="form.actual_behavior" class="textarea" rows="3"></textarea>
          </label>
          <div v-if="submitMessage" class="feedback-message field--full">{{ submitMessage }}</div>
          <div class="actions-row field--full">
            <button class="button" type="submit">{{ submitting ? '提交中...' : '提交反馈' }}</button>
          </div>
        </form>
      </article>
    </section>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import AppShell from '../components/layout/AppShell.vue'
import {
  apiGet,
  apiPost,
  buildSubmittedIssueSearch,
  type FeedbackCreatePayload,
  type PaginatedResponse,
  type SubmittedIssue,
} from '../services/api'

const submittedIssues = ref<SubmittedIssue[]>([])
const issuesLoading = ref(false)
const duplicateIssues = ref<SubmittedIssue[]>([])
const submitting = ref(false)
const submitMessage = ref('')

const filters = reactive({
  keyword: '',
  type: 'all',
})

const form = reactive<FeedbackCreatePayload>({
  type: 'bug',
  related_id: '',
  raw_content: '',
  expected_behavior: '',
  actual_behavior: '',
})

const normalizedRelatedId = computed(() => form.related_id.trim())

async function loadSubmittedIssues(): Promise<void> {
  issuesLoading.value = true
  const response = await apiGet<PaginatedResponse<SubmittedIssue>>(buildSubmittedIssueSearch(filters))
  submittedIssues.value = response.success ? response.data.items : []
  issuesLoading.value = false
}

async function loadDuplicateIssues(): Promise<void> {
  if (!normalizedRelatedId.value) {
    duplicateIssues.value = []
    return
  }
  const response = await apiGet<PaginatedResponse<SubmittedIssue>>(
    buildSubmittedIssueSearch({ related_id: normalizedRelatedId.value }),
  )
  duplicateIssues.value = response.success ? response.data.items : []
}

async function submitFeedback(): Promise<void> {
  submitting.value = true
  submitMessage.value = ''

  const payload: FeedbackCreatePayload = {
    type: form.type,
    related_id: form.related_id,
    raw_content: form.raw_content,
    expected_behavior: form.expected_behavior || undefined,
    actual_behavior: form.actual_behavior || undefined,
  }
  const response = await apiPost<{ id: string; status: string; created_at: string }, FeedbackCreatePayload>(
    '/api/feedback',
    payload,
  )

  if (response.success) {
    submitMessage.value = `提交成功，反馈编号 ${response.data.id}`
    form.type = 'bug'
    form.related_id = ''
    form.raw_content = ''
    form.expected_behavior = ''
    form.actual_behavior = ''
    duplicateIssues.value = []
  } else {
    submitMessage.value = response.message || '提交失败，请检查输入后重试'
  }

  submitting.value = false
}

watch(
  () => form.related_id,
  () => {
    submitMessage.value = ''
  },
)

onMounted(async () => {
  await loadSubmittedIssues()
})
</script>
