<template>
  <form class="admin-auth-card" @submit.prevent="$emit('submit', adminUsername, adminPassword)">
    <p class="eyebrow">Restricted Area</p>
    <h2>管理员登录</h2>
    <p>输入账号密码后加载队列和草稿。</p>
    <label class="field field--full">
      <span>用户名</span>
      <input v-model="adminUsername" class="input" type="text" autocomplete="username" placeholder="admin" />
    </label>
    <label class="field field--full">
      <span>密码</span>
      <input
        v-model="adminPassword"
        class="input"
        type="password"
        autocomplete="current-password"
        placeholder="********"
      />
    </label>
    <div v-if="authMessage" class="feedback-message feedback-message--error">{{ authMessage }}</div>
    <button class="button" type="submit" :disabled="isLoggingIn">{{ isLoggingIn ? '登录中…' : '登录' }}</button>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  authMessage: string
  isLoggingIn: boolean
}>()

defineEmits<{
  submit: [username: string, password: string]
}>()

const adminUsername = ref('')
const adminPassword = ref('')
</script>
