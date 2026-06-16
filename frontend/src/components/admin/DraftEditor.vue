<template>
  <article id="draft-panel" class="issue-editor">
    <header class="studio-section-head">
      <div>
        <span>Issue Draft</span>
        <h3>{{ statusLabel }}</h3>
      </div>
      <p>{{ statusDescription }}</p>
    </header>

    <div class="issue-editor__meta issue-editor__meta--badges">
      <span>{{ relatedIdSummary }}</span>
      <span>{{ activeBatchId || '待建批' }}</span>
      <span>{{ updatedAtLabel }}</span>
    </div>

    <section class="batch-insight-grid" aria-label="批次摘要信息">
      <article class="batch-insight-card">
        <span>批次条目数</span>
        <strong>{{ reviewItems.length }}</strong>
      </article>
      <article class="batch-insight-card">
        <span>关联标识数</span>
        <strong>{{ relatedIdCount }}</strong>
      </article>
      <article class="batch-insight-card">
        <span>最近保存</span>
        <strong>{{ updatedAtLabel }}</strong>
      </article>
    </section>

    <div class="draft-editor-note">
      <strong>{{ editorHeadline }}</strong>
      <p>{{ editorHint }}</p>
    </div>

    <label class="field field--full issue-title-field">
      <span>Issue 标题</span>
      <small class="field-helper">标题保持聚焦，优先写清问题对象和结果。</small>
      <input :value="draftForm.title" class="input" :readonly="!currentDraftId" @input="onTitleChange" />
    </label>
    <label class="field field--full issue-body-field">
      <span>Issue 正文</span>
      <small class="field-helper">正文按摘要、背景、期望、实际和影响展开，便于直接提交到 GitHub。</small>
      <textarea :value="draftForm.body_markdown" class="textarea textarea--editor" rows="18" :readonly="!currentDraftId" @input="onBodyChange"></textarea>
    </label>

    <div v-if="message" class="feedback-message draft-message">{{ message }}</div>
    <section v-if="showChecklist" class="submission-readiness-card" aria-label="提交前确认信息">
      <strong>提交前确认</strong>
      <p>{{ checklistSummary }}</p>
      <div class="submission-readiness-card__facts">
        <span>标题 {{ titleLength }} 字</span>
        <span>正文 {{ bodyLength }} 字</span>
        <span>{{ sectionCount }} 个 Markdown 小节</span>
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
      <button class="button button--secondary" type="button" :disabled="!activeBatchId || integratingDraft" @click="$emit('integrateDraft')">
        {{ integratingDraft ? '生成中...' : '生成草稿' }}
      </button>
      <button class="button button--quiet" type="button" :disabled="!currentDraftId || savingDraft" @click="$emit('saveDraft')">
        {{ savingDraft ? '保存中...' : '保存草稿' }}
      </button>
      <button class="button" type="button" :disabled="!canSubmit || submittingDraft" @click="$emit('submitDraft')">
        {{ submittingDraft ? '提交中...' : '提交 GitHub' }}
      </button>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { DraftSubmitResponse, FeedbackItem } from '../../services/api'

export type DraftForm = { title: string; body_markdown: string }

defineProps<{
  activeBatchId: string
  currentDraftId: string
  draftForm: DraftForm
  submissionResult: DraftSubmitResponse | null
  statusLabel: string
  statusDescription: string
  relatedIdSummary: string
  updatedAtLabel: string
  editorHeadline: string
  editorHint: string
  showChecklist: boolean
  checklistSummary: string
  reviewItems: FeedbackItem[]
  relatedIdCount: number
  titleLength: number
  bodyLength: number
  sectionCount: number
  canSubmit: boolean
  message: string
  savingDraft: boolean
  submittingDraft: boolean
  integratingDraft: boolean
}>()

const emit = defineEmits<{
  integrateDraft: []
  saveDraft: []
  submitDraft: []
  'update:draftForm': [form: DraftForm]
}>()

function onTitleChange(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:draftForm', { title: target.value, body_markdown: '' })
}

function onBodyChange(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:draftForm', { title: '', body_markdown: target.value })
}
</script>
