<template>
  <div class="page-shell" :class="{ 'page-shell--wide': wide }">
    <header class="page-shell__header">
      <div class="hero-block">
        <a class="brand-mark" href="https://monkeycode-ai.com/" target="_blank" rel="noreferrer" aria-label="MonkeyCode 官网">
          <img src="https://monkeycode-ai.com/logo-light.png" alt="" />
          <span>MonkeyCode</span>
        </a>
        <div class="page-shell__title">
          <span>{{ title }}</span>
          <p>{{ description }}</p>
        </div>
      </div>
      <div class="shell-actions">
        <nav class="top-nav" aria-label="主导航">
          <RouterLink to="/">
            <span class="top-nav__eyebrow">Front Desk</span>
            <strong>用户提交页</strong>
          </RouterLink>
        </nav>
      </div>
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
  wide?: boolean
}>()
</script>
