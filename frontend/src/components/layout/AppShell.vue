<template>
  <div class="page-shell">
    <header class="page-shell__header">
      <div>
        <p class="eyebrow">Issue Aggregator</p>
        <h1>{{ title }}</h1>
        <p class="page-shell__description">{{ description }}</p>
      </div>
      <nav class="top-nav">
        <RouterLink to="/">用户页</RouterLink>
        <RouterLink to="/admin">后台页</RouterLink>
      </nav>
    </header>
    <main class="page-shell__main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>
