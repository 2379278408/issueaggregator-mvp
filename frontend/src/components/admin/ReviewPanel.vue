<template>
  <article id="review-panel" class="topic-canvas">
    <header class="studio-section-head">
      <div>
        <span>Topic Canvas</span>
        <h3>{{ headline }}</h3>
      </div>
      <p>{{ description }}</p>
    </header>

    <section class="topic-summary" :class="decisionToneClass">
      <span>判断</span>
      <strong>{{ decision.title }}</strong>
      <p>{{ decision.description }}</p>
    </section>

    <div class="topic-facts">
      <article>
        <span>主题</span>
        <strong>{{ primaryRelatedId || '待选择' }}</strong>
      </article>
      <article>
        <span>信号</span>
        <strong>{{ items.length }}</strong>
      </article>
      <article>
        <span>缺失</span>
        <strong>{{ missingCount }}</strong>
      </article>
    </div>

    <div class="evidence-list">
      <article v-for="item in items" :key="item.id" class="evidence-card">
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
      <div v-if="!items.length" class="empty-state">
        <strong class="empty-state__title">等待生成主题画布</strong>
        <span class="empty-state__hint">先在左侧选择反馈，这里会汇总主题、缺失信息和聚合判断。</span>
      </div>
    </div>

    <div v-if="message" class="feedback-message">{{ message }}</div>
    <div class="studio-actions">
      <button
        class="button button--secondary"
        type="button"
        :disabled="queueStatus !== 'pending' || creatingBatch"
        @click="$emit('createBatch')"
      >
        {{ creatingBatch ? '创建中...' : isMixed ? '确认建批' : '创建批次' }}
      </button>
      <button
        class="button"
        type="button"
        :disabled="!activeBatchId || integratingDraft"
        @click="$emit('integrateDraft')"
      >
        {{ integratingDraft ? '生成中...' : '生成草稿' }}
      </button>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { FeedbackItem } from '../../services/api'

defineProps<{
  items: FeedbackItem[]
  headline: string
  description: string
  decision: { title: string; description: string }
  decisionToneClass: string
  primaryRelatedId: string
  missingCount: number
  message: string
  creatingBatch: boolean
  integratingDraft: boolean
  queueStatus: string
  activeBatchId: string
  isMixed: boolean
}>()

defineEmits<{
  createBatch: []
  integrateDraft: []
}>()

const typeLabelMap: Record<string, string> = { bug: '缺陷', feature: '新功能', enhancement: '优化', question: '问题' }

function getTypeLabel(type: string): string {
  return typeLabelMap[type] || type
}

function getMissingFieldCount(item: FeedbackItem): number {
  let count = 0
  if (!item.expected_behavior) count += 1
  if (!item.actual_behavior) count += 1
  return count
}
</script>
