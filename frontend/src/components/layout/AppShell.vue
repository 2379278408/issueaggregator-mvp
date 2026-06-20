<template>
  <div class="page-shell" :class="{ 'page-shell--wide': wide }">
    <header class="page-shell__header">
      <div class="hero-block">
        <a
          class="brand-mark"
          href="https://monkeycode-ai.com/"
          target="_blank"
          rel="noreferrer"
          aria-label="MonkeyCode 官网"
        >
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
        <ThemeToggle />
      </div>
    </header>
    <main class="page-shell__main">
      <slot />
    </main>
    <ToastNotification ref="toastRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, provide, type ComponentPublicInstance } from 'vue'
import ToastNotification from '../common/ToastNotification.vue'
import ThemeToggle from './ThemeToggle.vue'
import { TOAST_KEY } from '../../composables/useToast'

defineProps<{
  title: string
  description: string
  wide?: boolean
}>()

const toastRef = ref<ComponentPublicInstance<typeof ToastNotification> | null>(null)

type ToastApi = {
  notify: (message: string) => void
  notifySuccess: (message: string) => void
  notifyWarning: (message: string) => void
  notifyError: (message: string) => void
  dismiss: (id: number) => void
}

const toastApi: ToastApi = {
  notify: (message: string) => toastRef.value?.notify(message),
  notifySuccess: (message: string) => toastRef.value?.notifySuccess(message),
  notifyWarning: (message: string) => toastRef.value?.notifyWarning(message),
  notifyError: (message: string) => toastRef.value?.notifyError(message),
  dismiss: (id: number) => toastRef.value?.dismiss(id),
}

provide(TOAST_KEY, toastApi)
</script>
