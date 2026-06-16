import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import ToastNotification from '../../components/common/ToastNotification.vue'

function hasToast(selector: string): boolean {
  return document.querySelector(`.toast-container ${selector}`) !== null
}

function countToasts(): number {
  return document.querySelectorAll('.toast-container .toast').length
}

describe('ToastNotification', () => {
  let wrapper: VueWrapper

  afterEach(() => {
    vi.useRealTimers()
    if (wrapper) {
      wrapper.unmount()
    }
    document.querySelectorAll('.toast-container').forEach((el) => el.remove())
  })

  it('renders nothing when no toasts', () => {
    wrapper = mount(ToastNotification)
    expect(hasToast('.toast')).toBe(false)
  })

  it('shows notify toast with info type', async () => {
    wrapper = mount(ToastNotification)
    ;(wrapper.vm as any).notify('hello world')
    await nextTick()
    expect(hasToast('.toast--info')).toBe(true)
    expect(document.querySelector('.toast--info')?.textContent).toContain('hello world')
  })

  it('shows notifySuccess toast', async () => {
    wrapper = mount(ToastNotification)
    ;(wrapper.vm as any).notifySuccess('done')
    await nextTick()
    expect(hasToast('.toast--success')).toBe(true)
  })

  it('shows notifyWarning toast', async () => {
    wrapper = mount(ToastNotification)
    ;(wrapper.vm as any).notifyWarning('caution')
    await nextTick()
    expect(hasToast('.toast--warning')).toBe(true)
  })

  it('shows notifyError toast', async () => {
    wrapper = mount(ToastNotification)
    ;(wrapper.vm as any).notifyError('boom')
    await nextTick()
    expect(hasToast('.toast--error')).toBe(true)
  })

  it('dismiss removes toast', async () => {
    wrapper = mount(ToastNotification)
    ;(wrapper.vm as any).notify('temp')
    await nextTick()
    ;(wrapper.vm as any).dismiss(0)
    await nextTick()
    expect(countToasts()).toBe(0)
  })

  it('auto-dismisses after default duration', async () => {
    vi.useFakeTimers()
    wrapper = mount(ToastNotification)
    ;(wrapper.vm as any).notify('auto')
    await nextTick()
    expect(countToasts()).toBe(1)
    vi.advanceTimersByTime(4001)
    await nextTick()
    expect(countToasts()).toBe(0)
  })

  it('dismiss is a no-op for unknown id', async () => {
    wrapper = mount(ToastNotification)
    ;(wrapper.vm as any).notify('only one')
    await nextTick()
    expect(() => (wrapper.vm as any).dismiss(999)).not.toThrow()
  })
})
