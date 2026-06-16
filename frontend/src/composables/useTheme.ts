import { ref, watchEffect } from 'vue'

const THEME_KEY = 'theme-preference'
const theme = ref<'light' | 'dark'>(
  typeof localStorage !== 'undefined' && (localStorage.getItem(THEME_KEY) as 'light' | 'dark') === 'dark'
    ? 'dark'
    : 'light',
)

function applyTheme(value: 'light' | 'dark'): void {
  document.documentElement.setAttribute('data-theme', value)
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(THEME_KEY, value)
  }
}

watchEffect(() => applyTheme(theme.value))

export function useTheme() {
  function toggle(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function setDark(): void {
    theme.value = 'dark'
  }

  function setLight(): void {
    theme.value = 'light'
  }

  return { theme, toggle, setDark, setLight }
}
