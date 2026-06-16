<template>
  <section class="duplicate-panel duplicate-panel--inline" :class="`duplicate-panel--${tone}`">
    <div class="studio-section-head studio-section-head--compact">
      <div>
        <span>Duplicate</span>
        <h3>{{ issues.length ? title : '查重' }}</h3>
      </div>
    </div>
    <div class="duplicate-panel__status">
      <span class="duplicate-panel__badge">{{ statusLabel }}</span>
      <strong>{{ actionTitle }}</strong>
    </div>
    <p v-if="issues.length">{{ summary }}</p>
    <p v-else>{{ hint }}</p>
    <p class="duplicate-panel__recommendation">{{ actionHint }}</p>
    <ul v-if="issues.length" class="duplicate-list duplicate-list--studio">
      <li v-for="issue in issues" :key="issue.issue_number">
        <a :href="issue.issue_url" target="_blank" rel="noreferrer">#{{ issue.issue_number }} {{ issue.title }}</a>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { SubmittedIssue } from '../../services/api'

defineProps<{
  issues: SubmittedIssue[]
  tone: string
  title: string
  statusLabel: string
  actionTitle: string
  summary: string
  hint: string
  actionHint: string
}>()
</script>
