<template>
  <div class="skeleton" aria-busy="true" aria-label="正在加载">
    <template v-if="variant === 'list'">
      <div v-for="i in rows" :key="i" class="skeleton__row">
        <span class="skeleton__line" :style="{ width: lineWidths[(i - 1) % lineWidths.length] }" />
        <span v-if="showMeta" class="skeleton__line skeleton__line--meta" />
      </div>
    </template>
    <template v-else-if="variant === 'card-grid'">
      <div v-for="i in rows" :key="i" class="skeleton__card">
        <span class="skeleton__line skeleton__line--heading" />
        <span class="skeleton__line" style="width: 80%" />
        <span class="skeleton__line" style="width: 55%" />
      </div>
    </template>
    <template v-else>
      <div v-for="i in rows" :key="i" class="skeleton__row">
        <span class="skeleton__line" style="width: 100%" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'list' | 'card-grid' | 'text'
    rows?: number
    showMeta?: boolean
  }>(),
  {
    variant: 'text',
    rows: 5,
    showMeta: false,
  },
)

const lineWidths = ['60%', '42%', '75%', '38%', '55%']
</script>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: var(--space-4, 16px);
  animation: skeleton-pulse 1.6s ease-in-out infinite;
}

.skeleton__row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton__line {
  display: block;
  height: 12px;
  border-radius: 6px;
  background: var(--color-border, rgba(31, 35, 40, 0.1));
}

.skeleton__line--meta {
  width: 100px;
  height: 10px;
}

.skeleton__line--heading {
  width: 50%;
  height: 16px;
  margin-bottom: 4px;
}

.skeleton__card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: var(--radius-control, 12px);
  border: 1px solid var(--color-border, rgba(31, 35, 40, 0.1));
}

@keyframes skeleton-pulse {
  0%,
  100% {
    opacity: 0.4;
  }
  50% {
    opacity: 0.75;
  }
}
</style>
