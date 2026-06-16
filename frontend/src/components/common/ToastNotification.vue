<template>
  <teleport to="body">
    <div v-if="toasts.length" class="toast-container" role="alert" aria-live="polite">
      <transition-group name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast"
          :class="`toast--${toast.type}`"
          @click="dismiss(toast.id)"
        >
          <span class="toast__icon">{{ iconMap[toast.type] }}</span>
          <span class="toast__message">{{ toast.message }}</span>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export type ToastType = 'info' | 'success' | 'warning' | 'error'

interface Toast {
  id: number
  type: ToastType
  message: string
}

const toasts = ref<Toast[]>([])
let nextId = 0

const iconMap: Record<ToastType, string> = {
  info: 'i',
  success: '✓',
  warning: '!',
  error: '✕',
}

function show(type: ToastType, message: string, duration = 4000) {
  const id = nextId++
  toasts.value = [...toasts.value, { id, type, message }]
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
}

function dismiss(id: number) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

function notify(message: string) {
  show('info', message)
}

function notifySuccess(message: string) {
  show('success', message)
}

function notifyWarning(message: string) {
  show('warning', message, 6000)
}

function notifyError(message: string) {
  show('error', message, 8000)
}

defineExpose({ notify, notifySuccess, notifyWarning, notifyError, dismiss })
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 380px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-card, 10px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  cursor: pointer;
  font-size: 14px;
  line-height: 1.5;
  transition: opacity 0.25s, transform 0.25s;
}

.toast__icon {
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
}

.toast--info {
  background: #e8f4fd;
  border: 1px solid #b6daf2;
  color: #0d3b66;
}

.toast--info .toast__icon {
  background: #0d3b66;
  color: #fff;
}

.toast--success {
  background: #e6f4ea;
  border: 1px solid #a8d5b0;
  color: #1a472a;
}

.toast--success .toast__icon {
  background: #1a472a;
  color: #fff;
}

.toast--warning {
  background: #fef3e2;
  border: 1px solid #f5c97e;
  color: #6b4a0f;
}

.toast--warning .toast__icon {
  background: #6b4a0f;
  color: #fff;
}

.toast--error {
  background: #fde8e8;
  border: 1px solid #f2b6b6;
  color: #661010;
}

.toast--error .toast__icon {
  background: #661010;
  color: #fff;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
</style>
