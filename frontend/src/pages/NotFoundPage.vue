<template>
  <AppShell title="页面不存在" description="您访问的路径不存在或已被移除。">
    <div class="not-found">
      <strong>404</strong>
      <p>您访问的路径不存在，请检查链接是否正确。</p>
      <router-link class="button" to="/">返回首页</router-link>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import AppShell from '../components/layout/AppShell.vue'
</script>

<style scoped>
.not-found {
  min-height: 40vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 16px;
}

.not-found strong {
  font-size: 3rem;
  color: var(--color-accent);
}
</style>
