import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'

const { apiGet, apiPost, buildPublicApiPath, buildSubmittedIssueSearch } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  buildPublicApiPath: vi.fn((path: string) => `/portal${path}`),
  buildSubmittedIssueSearch: vi.fn((params: { related_id?: string; type?: string; keyword?: string }) => {
    if (params.related_id) {
      return `/portal/issues/submitted/search?related_id=${params.related_id}`
    }
    const query = new URLSearchParams()
    if (params.keyword?.trim()) {
      query.set('keyword', params.keyword.trim())
    }
    if (params.type && params.type !== 'all') {
      query.set('type', params.type)
    }
    return query.size ? `/portal/issues/submitted/search?${query.toString()}` : '/portal/issues/submitted'
  }),
}))

import UserHomePage from './UserHomePage.vue'

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
  buildPublicApiPath,
  buildSubmittedIssueSearch,
}))

describe('UserHomePage', () => {
  beforeEach(() => {
    vi.useRealTimers()
    apiGet.mockReset()
    apiPost.mockReset()
    buildPublicApiPath.mockClear()
    buildSubmittedIssueSearch.mockClear()
    window.history.replaceState({}, '', '/intake')
    document.title = 'Issue Intake'
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })
  })

  it('loads submitted issues on mount', async () => {
    apiGet.mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            issue_number: 101,
            title: 'Existing issue',
            issue_url: 'https://github.com/org/repo/issues/101',
            related_id: 'editor-copy-button',
            type: 'bug',
            submitted_at: '2026-06-11T10:30:00Z',
          },
        ],
        total: 6,
      },
    })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: { template: '<div><slot /></div>' },
        },
      },
    })

    await flushPromises()

    expect(apiGet).toHaveBeenCalledWith('/portal/issues/submitted')
    expect(wrapper.text()).toContain('已提交 Issue6')
    expect(wrapper.text()).toContain('Existing issue')
  })

  it('recovers when submitted issues fail to load', async () => {
    apiGet.mockResolvedValue({ success: false, message: '已提交 Issue 加载失败，请稍后重试。' })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: { AppShell: { template: '<div><slot /></div>' } },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('已提交 Issue 加载失败')
    expect(wrapper.text()).not.toContain('加载中')
  })

  it('shows empty search guidance when filtered history has no result', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 3 } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="搜索标识或关键词"]').setValue('toolbar')
    await wrapper.get('select').setValue('bug')
    await wrapper.get('button.button--quiet').trigger('click')
    await flushPromises()

    expect(apiGet).toHaveBeenLastCalledWith('/portal/issues/submitted/search?keyword=toolbar&type=bug')
    expect(wrapper.text()).toContain('当前结果 0 条')
    expect(wrapper.text()).toContain('已按 关键词 toolbar / 类型 缺陷 筛选')
    expect(wrapper.text()).toContain('没有匹配结果')
  })

  it('keeps the last submitted issue total when a later refresh fails', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              issue_number: 101,
              title: 'Existing issue',
              issue_url: 'https://github.com/org/repo/issues/101',
              related_id: 'editor-copy-button',
              type: 'bug',
              submitted_at: '2026-06-11T10:30:00Z',
            },
          ],
          total: 6,
        },
      })
      .mockResolvedValueOnce({ success: false, message: '已提交 Issue 加载失败，请稍后重试。' })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button.button--quiet').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('已提交 Issue6')
    expect(wrapper.text()).toContain('已提交 Issue 加载失败')
  })

  it('requires an explicit feedback type selection', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    expect(wrapper.text()).toContain('先选择反馈类型')

    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(apiPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请先选择反馈类型')
  })

  it('marks feedback type card as active after selecting a type', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('.feedback-type-card--active').exists()).toBe(true)
    expect(wrapper.text()).toContain('缺陷')
  })

  it('shows duplicate issue hints after related_id blur', async () => {
    vi.useFakeTimers()
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              issue_number: 102,
              title: 'Duplicate issue',
              issue_url: 'https://github.com/org/repo/issues/102',
              related_id: 'editor-copy-button',
              type: 'bug',
              submitted_at: '2026-06-11T10:30:00Z',
            },
          ],
        },
      })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(wrapper.text()).toContain('发现同标识')
    expect(wrapper.text()).toContain('Duplicate issue')
    vi.useRealTimers()
  })

  it('looks up duplicate issues while typing a valid related id', async () => {
    vi.useFakeTimers()
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } }).mockResolvedValueOnce({
      success: true,
      data: {
        items: [
          {
            issue_number: 103,
            title: 'Typing duplicate issue',
            issue_url: 'https://github.com/org/repo/issues/103',
            related_id: 'test',
            type: 'bug',
            submitted_at: '2026-06-11T10:30:00Z',
          },
        ],
      },
    })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('test')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(apiGet).toHaveBeenNthCalledWith(2, '/portal/issues/submitted/search?related_id=test')
    expect(wrapper.text()).toContain('Typing duplicate issue')
    vi.useRealTimers()
  })

  it('shows continue guidance when duplicate lookup finds no matching issue', async () => {
    vi.useFakeTimers()
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('test')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(wrapper.text()).toContain('当前没有找到同主题记录。')
    expect(wrapper.text()).toContain('可以继续填写正文并提交')
    vi.useRealTimers()
  })

  it('falls back to related keyword matches when exact related id is absent', async () => {
    vi.useFakeTimers()
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              issue_number: 104,
              title: 'Related test issue',
              issue_url: 'https://github.com/org/repo/issues/104',
              related_id: 'test-callbcak',
              type: 'question',
              submitted_at: '2026-06-11T10:30:00Z',
            },
          ],
        },
      })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('test-callback')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(apiGet).toHaveBeenNthCalledWith(2, '/portal/issues/submitted/search?related_id=test-callback')
    expect(apiGet).toHaveBeenNthCalledWith(3, '/portal/issues/submitted/search?keyword=test')
    expect(wrapper.text()).toContain('发现相近主题')
    expect(wrapper.text()).toContain('Related test issue')
    vi.useRealTimers()
  })

  it('shows duplicate lookup error when search API returns success false', async () => {
    vi.useFakeTimers()
    apiGet.mockImplementation(async (url: string) => {
      if (url.includes('related_id=test')) {
        return { success: false, message: '同主题检查失败，请稍后重试。' }
      }
      return { success: true, data: { items: [] } }
    })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('test')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(wrapper.text()).toContain('同主题检查失败，请稍后重试。')
    vi.useRealTimers()
  })

  it('ignores stale duplicate results after related id is cleared', async () => {
    vi.useFakeTimers()
    let resolveDuplicateLookup: (value: unknown) => void = () => undefined
    const pendingDuplicateLookup = new Promise((resolve) => {
      resolveDuplicateLookup = resolve
    })

    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockImplementationOnce(() => pendingDuplicateLookup)

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('test')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('')
    await flushPromises()

    resolveDuplicateLookup({
      success: true,
      data: {
        items: [
          {
            issue_number: 105,
            title: 'Stale duplicate issue',
            issue_url: 'https://github.com/org/repo/issues/105',
            related_id: 'test',
            type: 'bug',
            submitted_at: '2026-06-11T10:30:00Z',
          },
        ],
      },
    })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Stale duplicate issue')
    expect(wrapper.text()).not.toContain('发现同标识')
    vi.useRealTimers()
  })

  it('normalizes related id before duplicate lookup', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('GitHub Submit_Flow')
    await wrapper.get('input[placeholder="editor-copy-button"]').trigger('blur')
    await flushPromises()

    expect((wrapper.get('input[placeholder="editor-copy-button"]').element as HTMLInputElement).value).toBe(
      'github-submit-flow',
    )
    expect(apiGet).toHaveBeenNthCalledWith(2, '/portal/issues/submitted/search?related_id=github-submit-flow')
    expect(apiGet).toHaveBeenNthCalledWith(3, '/portal/issues/submitted/search?keyword=github')
  })

  it('keeps unsupported separators so validation can block submission', async () => {
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('github/submit-flow')
    await wrapper.get('input[placeholder="editor-copy-button"]').trigger('blur')
    await flushPromises()

    expect((wrapper.get('input[placeholder="editor-copy-button"]').element as HTMLInputElement).value).toBe(
      'github/submit-flow',
    )
    expect(apiGet.mock.calls).not.toContainEqual(['/portal/issues/submitted/search?related_id=github/submit-flow'])
  })

  it('shows related id as pending until the format is valid', async () => {
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('github/submit-flow')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await flushPromises()

    expect(wrapper.text()).toContain('关联标识格式需为小写英文、数字和短横线')
  })

  it('shows helper text about related id format', async () => {
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('空格和下划线会自动转成短横线')
  })

  it('submits feedback and shows success message', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })
    apiPost.mockResolvedValue({
      success: true,
      data: {
        id: 'fb_001',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(apiPost).toHaveBeenCalled()
    expect(apiPost.mock.calls[0][0]).toBe('/portal/feedback')
    expect(apiPost.mock.calls[0][1]).toMatchObject({
      type: 'bug',
      related_id: 'editor-copy-button',
      raw_content: 'feedback body',
    })
    expect(wrapper.text()).toContain('提交成功，反馈编号 fb_001')
    expect(wrapper.text()).toContain('最近一次提交')
    expect(wrapper.text()).toContain('editor-copy-button')
  })

  it('copies related id and jumps to history after successful submission', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
    apiPost.mockResolvedValue({
      success: true,
      data: {
        id: 'fb_003',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    const actionButtons = wrapper.findAll('.submission-summary__actions button')
    await actionButtons[0].trigger('click')
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('editor-copy-button')
    expect(wrapper.text()).toContain('已复制')

    await actionButtons[1].trigger('click')
    await flushPromises()
    expect(apiGet.mock.calls).toContainEqual(['/portal/issues/submitted/search?keyword=editor-copy-button'])
  })

  it('keeps submission success message when history refresh fails', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: false, message: '已提交 Issue 加载失败，请稍后重试。' })
    apiPost.mockResolvedValue({
      success: true,
      data: {
        id: 'fb_002',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('提交成功，反馈编号 fb_002')
    expect(wrapper.text()).toContain('已提交 Issue 加载失败，请稍后重试。')
  })

  it('recovers when feedback submission rejects', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })
    apiPost.mockRejectedValue(new Error('network down'))

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('提交失败，请检查网络后重试')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })

  it('shows local validation for invalid related id', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('提交流程')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(apiPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('关联标识请使用小写英文、数字和短横线')
  })

  it('ignores stale duplicate results after successful submission reset', async () => {
    vi.useFakeTimers()
    let resolveDuplicateLookup: (value: unknown) => void = () => undefined
    const pendingDuplicateLookup = new Promise((resolve) => {
      resolveDuplicateLookup = resolve
    })

    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockImplementationOnce(() => pendingDuplicateLookup)
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
    apiPost.mockResolvedValue({
      success: true,
      data: { id: 'fb_010', status: 'pending', created_at: '2026-06-11T10:00:00Z' },
    })

    const wrapper = mount(UserHomePage, {
      global: { stubs: { AppShell: { template: '<div><slot /></div>' } } },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    resolveDuplicateLookup({
      success: true,
      data: {
        items: [
          {
            issue_number: 120,
            title: 'Late duplicate issue',
            issue_url: 'https://github.com/org/repo/issues/120',
            related_id: 'editor-copy-button',
            type: 'bug',
            submitted_at: '2026-06-11T10:30:00Z',
          },
        ],
      },
    })
    await flushPromises()

    expect((wrapper.get('input[placeholder="editor-copy-button"]').element as HTMLInputElement).value).toBe('')
    expect(wrapper.text()).toContain('提交成功，反馈编号 fb_010')
    expect(wrapper.text()).not.toContain('Late duplicate issue')
    vi.useRealTimers()
  })
})
