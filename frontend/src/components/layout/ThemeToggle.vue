<template>
  <button
    class="theme-toggle"
    :aria-label="isDark ? '切换到亮色模式' : '切换到深色模式'"
    :title="isDark ? '切换到亮色模式' : '切换到深色模式'"
    @click="toggle"
  >
    <span class="theme-toggle__icon" aria-hidden="true">{{ isDark ? '☀' : '☽' }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '../../composables/useTheme'

const { theme, toggle } = useTheme()
const isDark = computed(() => theme.value === 'dark')
</script>
