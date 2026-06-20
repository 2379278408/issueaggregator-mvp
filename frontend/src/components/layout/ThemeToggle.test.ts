import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { useTheme } from '../../composables/useTheme'

import ThemeToggle from './ThemeToggle.vue'

describe('ThemeToggle', () => {
  it('renders dark mode icon and correct aria-label when theme is light', () => {
    useTheme().setLight()
    const wrapper = mount(ThemeToggle)
    expect(wrapper.get('button').attributes('aria-label')).toBe('切换到深色模式')
    expect(wrapper.get('.theme-toggle__icon').text()).toBe('☽')
  })

  it('renders light mode icon and correct aria-label when theme is dark', () => {
    useTheme().setDark()
    const wrapper = mount(ThemeToggle)
    expect(wrapper.get('button').attributes('aria-label')).toBe('切换到亮色模式')
    expect(wrapper.get('.theme-toggle__icon').text()).toBe('☀')
  })

  it('toggles theme from light to dark on click', async () => {
    useTheme().setLight()
    const wrapper = mount(ThemeToggle)
    await wrapper.get('button').trigger('click')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('toggles theme back to light on second click', async () => {
    useTheme().setDark()
    const wrapper = mount(ThemeToggle)
    await wrapper.get('button').trigger('click')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })
})
