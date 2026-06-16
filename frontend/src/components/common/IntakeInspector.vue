<template>
  <aside class="intake-inspector">
    <section class="intake-checklist-panel">
      <div class="inspector-section-head">
        <span>Readiness</span>
        <strong>提交前检查</strong>
      </div>
      <div class="intake-checklist">
        <article class="intake-checklist__item" :class="{ 'is-ready': Boolean(type) }">
          <strong>类型</strong>
          <span>{{ typeLabel || '待选择' }}</span>
        </article>
        <article class="intake-checklist__item" :class="{ 'is-ready': hasValidRelatedId }">
          <strong>标识</strong>
          <span>{{ normalizedRelatedId || '待输入' }}</span>
        </article>
        <article class="intake-checklist__item" :class="{ 'is-ready': Boolean(rawContent) }">
          <strong>正文</strong>
          <span>{{ rawContent ? '已填写核心描述' : '待填写' }}</span>
        </article>
        <article class="intake-checklist__item" :class="{ 'is-ready': hasContext }">
          <strong>上下文</strong>
          <span>{{ hasContext ? contextSummary : '已留空' }}</span>
        </article>
      </div>
    </section>

    <section class="history-panel">
      <div class="studio-section-head">
        <div>
          <span>History</span>
          <h3>历史记录</h3>
        </div>
        <p>{{ historySummaryTitle }}</p>
      </div>
      <div class="history-search">
        <input v-model="keywordModel" class="input" placeholder="搜索标识或关键词" />
        <select v-model="typeFilterModel" class="select">
          <option value="all">全部</option>
          <option value="bug">缺陷</option>
          <option value="feature">新功能</option>
          <option value="enhancement">优化</option>
          <option value="question">问题</option>
        </select>
        <button class="button button--quiet" type="button" @click="$emit('search', keywordModel, typeFilterModel)">
          搜索
        </button>
      </div>
      <div class="history-inline-summary">{{ historySummaryHint }}</div>
      <div v-if="historyMessage" class="feedback-message feedback-message--subtle">{{ historyMessage }}</div>
      <div class="history-list">
        <article v-for="issue in issues" :key="issue.issue_number" class="history-card">
          <div class="history-card__meta">
            <span class="history-card__type">{{ getTypeLabel(issue.type) }}</span>
            <strong class="history-card__number">#{{ issue.issue_number }}</strong>
          </div>
          <a :href="issue.issue_url" target="_blank" rel="noreferrer">{{ issue.title }}</a>
          <span class="history-card__related">{{ issue.related_id }}</span>
        </article>
        <SkeletonLoader v-if="loading" variant="list" :rows="3" />
        <div v-if="!issues.length && !loading" class="empty-state">
          <strong class="empty-state__title">{{ emptyTitle }}</strong>
          <span class="empty-state__hint">{{ emptyHint }}</span>
        </div>
      </div>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SubmittedIssue } from '../../services/api'
import SkeletonLoader from './SkeletonLoader.vue'
import { getTypeLabel } from './IntakeInspector.utils'

const props = defineProps<{
  type: string
  typeLabel: string
  hasValidRelatedId: boolean
  normalizedRelatedId: string
  rawContent: string
  hasContext: boolean
  contextSummary: string
  issues: SubmittedIssue[]
  loading: boolean
  historyMessage: string
  historySummaryTitle: string
  historySummaryHint: string
  emptyTitle: string
  emptyHint: string
  keyword: string
  typeFilter: string
}>()

defineEmits<{
  search: [keyword: string, typeFilter: string]
}>()

const keywordModel = ref(props.keyword)
const typeFilterModel = ref(props.typeFilter)

watch(
  () => props.keyword,
  (v) => {
    keywordModel.value = v
  },
)
watch(
  () => props.typeFilter,
  (v) => {
    typeFilterModel.value = v
  },
)
</script>
