<template>
  <article id="review-panel" class="topic-canvas">
    <header class="studio-section-head studio-section-head--compact">
      <div>
        <span>Topic Canvas</span>
        <h3>{{ headline }}</h3>
      </div>
      <p>{{ description }}</p>
    </header>

    <section class="topic-summary topic-summary--compact" :class="decisionToneClass">
      <span>判断</span>
      <strong>{{ decision.title }}</strong>
      <p>{{ decision.description }}</p>
    </section>

    <div class="topic-facts topic-facts--compact">
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
      <details v-for="(item, index) in items" :key="item.id" class="evidence-card" :open="index === 0">
        <summary class="evidence-card__summary-toggle">
          <div class="evidence-card__meta">
            <span>{{ getTypeLabel(item.type) }}</span>
            <strong>{{ item.related_id }}</strong>
            <span>{{ getMissingFieldCount(item) ? `缺失 ${getMissingFieldCount(item)} 项` : '信息完整' }}</span>
          </div>
          <section class="evidence-card__summary">
            <span>反馈摘要</span>
            <p>{{ excerpt(item.raw_content) }}</p>
          </section>
          <small class="evidence-card__toggle-hint">查看期望与实际</small>
        </summary>
        <div class="evidence-card__detail">
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
        </div>
      </details>
      <div v-if="!items.length" class="empty-state">
        <strong class="empty-state__title">等待生成主题画布</strong>
        <span class="empty-state__hint">先在左侧选择反馈，这里会汇总主题、缺失信息和聚合判断。</span>
      </div>
    </div>

    <div v-if="message" class="feedback-message">{{ message }}</div>
    <section class="review-action-callout review-action-callout--compact" aria-label="当前主动作提示">
      <div>
        <span>当前动作</span>
        <strong>{{ actionTitle }}</strong>
        <p>{{ actionDescription }}</p>
      </div>
    </section>
    <div class="studio-actions review-actions">
      <button
        class="button"
        type="button"
        :disabled="queueStatus !== 'pending' || creatingBatch"
        @click="$emit('createBatch')"
      >
        {{ creatingBatch ? '创建中...' : isMixed ? '确认建批' : '创建批次' }}
      </button>
      <button
        class="button button--secondary"
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
import { computed } from 'vue'
import type { FeedbackItem } from '../../services/api'

const props = defineProps<{
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

function excerpt(text: string, maxLength = 120): string {
  return text.length <= maxLength ? text : `${text.slice(0, maxLength)}...`
}

const actionTitle = computed(() => {
  if (props.activeBatchId) return '批次已经就绪，继续生成草稿'
  if (!props.items.length) return '先从左侧选择一组反馈'
  if (props.isMixed) return '当前主题需要先拆分再建批'
  return '确认当前主题后创建批次'
})

const actionDescription = computed(() => {
  if (props.activeBatchId) return '当前主题已经通过审阅阶段，主流程下一步是生成结构化草稿并切入编辑区。'
  if (!props.items.length) return '左侧队列会把原始反馈送入这里，当前主面板负责做主题判断与建批决策。'
  if (props.isMixed) return '这一组反馈涉及多个关联标识，先缩小主题范围，再创建更聚焦的批次。'
  return '当主题一致且信息基本可用时，优先创建批次，再把上下文送入草稿编辑流程。'
})
</script>
