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
          <strong>{{ submittedIssues.length }}</strong>
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
            <div class="composer-row">
              <label class="field">
                <span>反馈类型</span>
                <select v-model="form.type" class="select">
                  <option value="bug">缺陷</option>
                  <option value="feature">新功能</option>
                  <option value="enhancement">优化</option>
                  <option value="question">问题</option>
                </select>
              </label>
              <label class="field">
                <span>关联标识</span>
                <input v-model="form.related_id" class="input" placeholder="editor-copy-button" @blur="loadDuplicateIssues" />
              </label>
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
          <section class="duplicate-panel">
            <div class="studio-section-head">
              <div>
              <span>Duplicate</span>
              <h3>{{ duplicateIssues.length ? '发现同主题' : '查重' }}</h3>
              </div>
            </div>
            <p v-if="duplicateIssues.length">已有 {{ duplicateIssues.length }} 条相关记录。</p>
            <p v-else>输入标识后显示相关 Issue。</p>
            <ul v-if="duplicateIssues.length" class="duplicate-list duplicate-list--studio">
              <li v-for="issue in duplicateIssues" :key="issue.issue_number">
                <a :href="issue.issue_url" target="_blank" rel="noreferrer">#{{ issue.issue_number }} {{ issue.title }}</a>
              </li>
            </ul>
          </section>

          <section class="history-panel">
            <div class="studio-section-head">
              <div>
                <span>History</span>
                <h3>历史记录</h3>
              </div>
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
              <button class="button button--secondary" type="button" @click="loadSubmittedIssues">搜索</button>
            </div>
            <div class="history-list">
              <article v-for="issue in submittedIssues" :key="issue.issue_number" class="history-card">
                <div>
                  <span>{{ getTypeLabel(issue.type) }} · #{{ issue.issue_number }}</span>
                  <strong>{{ issue.related_id }}</strong>
                </div>
                <a :href="issue.issue_url" target="_blank" rel="noreferrer">{{ issue.title }}</a>
              </article>
              <div v-if="!submittedIssues.length && !issuesLoading" class="empty-state">暂无历史记录。</div>
              <div v-if="issuesLoading" class="empty-state">正在加载...</div>
            </div>
          </section>
        </aside>
      </section>
    </section>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

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
}

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

function getTypeLabel(type: string): string {
  return typeLabelMap[type] || type
}

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
    buildPublicApiPath('/feedback'),
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
