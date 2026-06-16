<template>
  <section class="submission-summary-card" aria-label="最近一次提交摘要">
    <div>
      <span class="submission-summary-card__eyebrow">最近一次提交</span>
      <strong>{{ submission.related_id }}</strong>
      <p>
        {{ submission.typeLabel }}反馈已进入待整理队列，反馈编号 {{ submission.id }}。
        <span v-if="submission.created_at">提交时间 {{ submission.created_at }}</span>
      </p>
    </div>
    <div class="submission-summary-card__actions">
      <button class="button button--quiet button--compact" type="button" @click="$emit('copy-related')">
        {{ copyLabel }}
      </button>
      <button class="button button--secondary button--compact" type="button" @click="$emit('view-history')">
        查看同标识历史
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  submission: { id: string; related_id: string; typeLabel: string; created_at: string }
  copyLabel: string
}>()

defineEmits<{
  'copy-related': []
  'view-history': []
}>()
</script>
