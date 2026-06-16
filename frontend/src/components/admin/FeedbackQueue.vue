<template>
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
        <button
          class="triage-tab triage-tab--sidebar"
          :class="{ 'is-active': queueStatus === 'pending' }"
          type="button"
          @click="$emit('switchQueue', 'pending')"
        >
          <span>待整理</span>
          <strong>{{ statusCounts.pending }}</strong>
        </button>
        <button
          class="triage-tab triage-tab--sidebar"
          :class="{ 'is-active': queueStatus === 'grouped' }"
          type="button"
          @click="$emit('switchQueue', 'grouped')"
        >
          <span>草稿中</span>
          <strong>{{ statusCounts.grouped }}</strong>
        </button>
        <button
          class="triage-tab triage-tab--sidebar"
          :class="{ 'is-active': queueStatus === 'submitted' }"
          type="button"
          @click="$emit('switchQueue', 'submitted')"
        >
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
        <button class="triage-nav-card" :class="{ 'is-active': activeSection === 'queue' }" type="button" @click="$emit('focusSection', 'queue')">
          <div><span>01</span><strong>反馈队列</strong></div>
          <small>{{ items.length }} 条</small>
        </button>
        <button class="triage-nav-card" :class="{ 'is-active': activeSection === 'review' }" type="button" @click="$emit('focusSection', 'review')">
          <div><span>02</span><strong>主题判断</strong></div>
          <small>{{ reviewItemCount }} 条</small>
        </button>
        <button class="triage-nav-card" :class="{ 'is-active': activeSection === 'draft' }" type="button" @click="$emit('focusSection', 'draft')">
          <div><span>03</span><strong>草稿编辑</strong></div>
          <small>{{ currentDraftId ? '可提交' : '待生成' }}</small>
        </button>
        <button class="triage-nav-card" :class="{ 'is-active': activeSection === 'audit' }" type="button" @click="$emit('focusSection', 'audit')">
          <div><span>04</span><strong>审计记录</strong></div>
          <small>{{ auditEventCount }} 条</small>
        </button>
      </div>
    </section>
  </aside>

  <article id="queue-panel" class="signal-stream">
    <header class="studio-section-head">
      <div>
        <span>Signal Stream</span>
        <h3>{{ heading }}</h3>
      </div>
      <p>{{ description }}</p>
    </header>

    <div class="queue-overview">
      <strong>{{ statusCounts[queueStatus] }}</strong>
      <span>{{ overviewLabel }}</span>
    </div>

    <div v-if="queueStatus === 'pending' && items.length" class="signal-actions">
      <button class="button button--quiet button--compact" type="button" @click="$emit('toggleSelectAll')">
        {{ allSelected ? '取消全选' : '一键勾选' }}
      </button>
      <span>已选 {{ selectedIds.length }} / {{ items.length }}</span>
    </div>

    <div class="signal-list">
      <section v-for="section in sections" :key="section.label" class="signal-group">
        <div class="signal-group__label">
          <strong>{{ section.label }}</strong>
          <span>{{ section.items.length }}</span>
        </div>
        <button
          v-for="item in section.items"
          :key="item.id"
          class="signal-card"
          :class="{ 'is-active': isActive(item) }"
          type="button"
          @click="$emit('itemClick', item)"
        >
          <div class="signal-card__meta">
            <span>{{ getTypeLabel(item.type) }}</span>
            <span>{{ describeTime(item) }}</span>
          </div>
          <div class="signal-card__title">
            <strong>{{ item.related_id }}</strong>
            <input
              v-if="queueStatus === 'pending'"
              :checked="selectedIds.includes(item.id)"
              type="checkbox"
              aria-label="选择反馈"
              @click.stop
              @change="$emit('toggleSelection', item.id)"
            />
          </div>
          <p>{{ excerpt(item.raw_content, 92) }}</p>
        </button>
      </section>
      <div v-if="!items.length && !loading" class="empty-state">
        <strong class="empty-state__title">当前队列为空</strong>
        <span class="empty-state__hint">切换到其他状态，或等待新的反馈进入这个阶段。</span>
      </div>
      <div v-if="loading" class="empty-state empty-state--loading">正在载入...</div>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { FeedbackItem } from '../../services/api'

export type QueueStatus = 'pending' | 'grouped' | 'submitted'
export type AdminSection = 'queue' | 'review' | 'draft' | 'audit'

const props = defineProps<{
  queueStatus: QueueStatus
  items: FeedbackItem[]
  sections: Array<{ label: string; items: FeedbackItem[] }>
  selectedIds: string[]
  loading: boolean
  statusCounts: Record<QueueStatus, number>
  heading: string
  description: string
  allSelected: boolean
  activeSection: AdminSection
  reviewItemCount: number
  currentDraftId: string
  auditEventCount: number
}>()

defineEmits<{
  switchQueue: [status: QueueStatus]
  toggleSelection: [id: string]
  itemClick: [item: FeedbackItem]
  toggleSelectAll: []
  focusSection: [section: AdminSection]
}>()

const typeLabelMap: Record<string, string> = { bug: '缺陷', feature: '新功能', enhancement: '优化', question: '问题' }
const overviewLabelMap: Record<QueueStatus, string> = {
  pending: '等待进入本轮整理的反馈',
  grouped: '已进入批次、可继续整理的反馈',
  submitted: '已经完成提交的反馈记录',
}

const overviewLabel = overviewLabelMap[props.queueStatus]

function getTypeLabel(type: string): string {
  return typeLabelMap[type] || type
}

function excerpt(text: string, maxLength = 96): string {
  return text.length <= maxLength ? text : `${text.slice(0, maxLength)}...`
}

function describeTime(item: FeedbackItem): string {
  const value = item.submitted_at || item.created_at
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value || '刚刚更新'
  const hours = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 3600000))
  if (hours < 1) return '1 小时内'
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`
  return parsed.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

function isActive(item: FeedbackItem): boolean {
  if (props.queueStatus === 'pending') return props.selectedIds.includes(item.id)
  return false
}
</script>
