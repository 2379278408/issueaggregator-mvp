<template>
  <section id="audit-panel" class="audit-stream audit-stream--secondary">
    <header class="studio-section-head">
      <div>
        <span>Security Events</span>
        <h3>最近审计事件</h3>
      </div>
      <p>查看最近的管理员鉴权失败和成功操作，便于快速回看安全链路。</p>
    </header>

    <div class="audit-stream__meta">
      <span>最近 {{ events.length }} 条</span>
      <button class="button button--quiet button--compact" type="button" :disabled="loading" @click="$emit('refresh')">
        {{ loading ? '刷新中...' : '刷新事件' }}
      </button>
    </div>

    <div class="audit-filters">
      <button
        v-for="option in filterOptions"
        :key="option.value"
        class="audit-filter-chip"
        :class="{ 'is-active': activeFilter === option.value }"
        type="button"
        :disabled="loading"
        @click="$emit('applyFilter', option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <div class="audit-filters audit-filters--time">
      <button
        v-for="option in timeRangeOptions"
        :key="option.value"
        class="audit-filter-chip"
        :class="{ 'is-active': activeTimeRange === option.value }"
        type="button"
        :disabled="loading"
        @click="$emit('applyTimeRange', option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <div class="audit-search">
      <input
        v-model="localKeyword"
        class="input"
        type="text"
        placeholder="按 IP、路径、动作或资源检索"
        :disabled="loading"
        @keydown.enter.prevent="$emit('applyKeyword', localKeyword)"
      />
      <button class="button button--quiet button--compact" type="button" :disabled="loading" @click="$emit('applyKeyword', localKeyword)">
        检索
      </button>
    </div>

    <div v-if="message" class="feedback-message feedback-message--subtle">{{ message }}</div>
    <div class="audit-list">
      <article v-for="event in events" :key="event.id" class="audit-card">
        <div class="audit-card__meta">
          <strong>{{ getEventLabel(event) }}</strong>
          <span>{{ describeTime(event.created_at) }}</span>
        </div>
        <p>{{ describeEvent(event) }}</p>
        <div class="audit-card__tags">
          <span>{{ event.client_ip }}</span>
          <span>{{ event.path }}</span>
          <span v-if="event.resource_id">{{ event.resource_id }}</span>
        </div>
      </article>
      <div v-if="!events.length && !loading" class="empty-state">
        <strong class="empty-state__title">暂无审计事件</strong>
        <span class="empty-state__hint">当管理员鉴权失败或完成关键操作后，这里会记录最近的安全链路。</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { AuditEventRecord } from '../../services/api'

export type AuditEventFilter = 'all' | 'admin_auth_failed' | 'admin_action_succeeded'
export type AuditTimeRange = 'all' | '10m' | '1h' | '24h'

const props = defineProps<{
  events: AuditEventRecord[]
  filterOptions: Array<{ value: AuditEventFilter; label: string }>
  timeRangeOptions: Array<{ value: AuditTimeRange; label: string }>
  activeFilter: AuditEventFilter
  activeTimeRange: AuditTimeRange
  keywordInput: string
  loading: boolean
  message: string
}>()

defineEmits<{
  refresh: []
  applyFilter: [value: AuditEventFilter]
  applyTimeRange: [value: AuditTimeRange]
  applyKeyword: [value: string]
  'update:keywordInput': [value: string]
}>()

const localKeyword = ref(props.keywordInput)

watch(() => props.keywordInput, (value) => {
  localKeyword.value = value
})

function getEventLabel(event: AuditEventRecord): string {
  if (event.event_type === 'admin_auth_failed') return '管理员鉴权失败'
  return event.action ? `管理员操作成功 · ${event.action}` : '管理员操作成功'
}

function describeTime(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function describeEvent(event: AuditEventRecord): string {
  if (event.event_type === 'admin_auth_failed') return `管理接口 ${event.path} 出现一次鉴权失败请求。`
  if (event.action && event.resource_id) return `管理员完成 ${event.action}，关联资源 ${event.resource_id}。`
  if (event.action) return `管理员完成 ${event.action}。`
  return `管理员请求 ${event.path} 执行成功。`
}
</script>
