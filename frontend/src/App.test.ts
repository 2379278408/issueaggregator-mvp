import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from './App.vue'

describe('App', () => {
  it('renders RouterView', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div>home</div>' } }],
    })
    router.push('/')
    await router.isReady()
    const wrapper = mount(App, {
      global: { plugins: [router] },
    })
    await wrapper.vm.$nextTick()
    expect(wrapper.html()).toContain('home')
  })

  it('renders nothing when no matching route', () => {
    const router = createRouter({
      history: createMemoryHistory('/missing'),
      routes: [],
    })
    const wrapper = mount(App, {
      global: { plugins: [router] },
    })
    expect(wrapper.findComponent({ name: 'RouterView' }).exists()).toBe(true)
  })
})
