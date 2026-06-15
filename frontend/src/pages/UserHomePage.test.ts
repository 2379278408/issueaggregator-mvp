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
    window.history.replaceState({}, '', '/intake?token=secret#composer')
    document.title = 'Issue Intake'
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    })
    Object.defineProperty(window.navigator, 'language', { value: 'zh-CN', configurable: true })
    Object.defineProperty(window.navigator, 'platform', { value: 'Linux x86_64', configurable: true })
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
          AppShell: {
            template: '<div><slot /></div>',
          },
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
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    expect(wrapper.text()).toContain('请选择反馈类型')

    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(apiPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请先选择反馈类型')
  })

  it('marks the feedback type step as ready after selecting a type', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('.feedback-type-picker').classes()).toContain('composer-stage--ready')
    expect(wrapper.find('.feedback-type-picker').classes()).toContain('feedback-type-picker--ready')
    expect(wrapper.find('.feedback-type-card--active').exists()).toBe(true)
    expect(wrapper.text()).toContain('缺陷')
  })

  it('shows duplicate issue hints after related_id blur', async () => {
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
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              issue_number: 106,
              title: 'Example duplicate issue',
              issue_url: 'https://github.com/org/repo/issues/106',
              related_id: 'github-submit-flow',
              type: 'bug',
              submitted_at: '2026-06-11T10:30:00Z',
            },
          ],
        },
      })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('input[placeholder="editor-copy-button"]').trigger('blur')
    await flushPromises()

    expect(wrapper.text()).toContain('发现同标识')
    expect(wrapper.text()).toContain('Duplicate issue')
    expect(wrapper.text()).toContain('优先复用现有主题')
  })

  it('looks up duplicate issues while typing a valid related id', async () => {
    vi.useFakeTimers()
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('test')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(wrapper.text()).toContain('同主题检查失败，请稍后重试。')
    expect(wrapper.text()).not.toContain('当前还没有找到同标识的已提交 Issue。')
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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

  it('cancels pending debounced lookup before applying a related id example', async () => {
    vi.useFakeTimers()
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              issue_number: 106,
              title: 'Example duplicate issue',
              issue_url: 'https://github.com/org/repo/issues/106',
              related_id: 'github-submit-flow',
              type: 'bug',
              submitted_at: '2026-06-11T10:30:00Z',
            },
          ],
        },
      })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('test')
    await wrapper.get('button.related-id-chip').trigger('click')
    await flushPromises()
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()

    expect(apiGet.mock.calls).toContainEqual(['/portal/issues/submitted/search?related_id=github-submit-flow'])
    expect(apiGet.mock.calls).not.toContainEqual(['/portal/issues/submitted/search?related_id=test'])
    expect(wrapper.text()).toContain('Example duplicate issue')
    vi.useRealTimers()
  })

  it('normalizes related id before duplicate lookup', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('GitHub Submit_Flow')
    await wrapper.get('input[placeholder="editor-copy-button"]').trigger('blur')
    await flushPromises()

    expect((wrapper.get('input[placeholder="editor-copy-button"]').element as HTMLInputElement).value).toBe('github-submit-flow')
    expect(apiGet).toHaveBeenNthCalledWith(2, '/portal/issues/submitted/search?related_id=github-submit-flow')
    expect(apiGet).toHaveBeenNthCalledWith(3, '/portal/issues/submitted/search?keyword=github-submit')
  })

  it('keeps unsupported separators so validation can block submission', async () => {
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('github/submit-flow')
    await wrapper.get('input[placeholder="editor-copy-button"]').trigger('blur')
    await flushPromises()

    expect((wrapper.get('input[placeholder="editor-copy-button"]').element as HTMLInputElement).value).toBe('github/submit-flow')
    expect(apiGet.mock.calls).not.toContainEqual(['/portal/issues/submitted/search?related_id=github/submit-flow'])
  })

  it('shows related id as pending until the format is valid', async () => {
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('github/submit-flow')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await flushPromises()

    expect(wrapper.text()).toContain('关联标识格式需为小写英文、数字和短横线')
    expect(wrapper.findAll('.intake-checklist__item.is-ready')).toHaveLength(3)
    expect(wrapper.text()).toContain('已带页面链接')
  })

  it('explains related id usage and applies examples', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('空格和下划线会自动转成短横线')
    await wrapper.get('button.related-id-chip').trigger('click')
    await flushPromises()

    expect((wrapper.get('input[placeholder="editor-copy-button"]').element as HTMLInputElement).value).toBe('github-submit-flow')
    expect(apiGet.mock.calls).toContainEqual(['/portal/issues/submitted/search?related_id=github-submit-flow'])
  })

  it('replaces form fields when switching quick templates', async () => {
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()

    const templateButtons = wrapper.findAll('.quick-template-card')
    await templateButtons[0].trigger('click')
    expect((wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').element as HTMLTextAreaElement).value).toContain('页面出现异常中断或卡住')
    expect((wrapper.get('textarea[placeholder="希望系统如何表现"]').element as HTMLTextAreaElement).value).toContain('流程应当连续完成')
    expect((wrapper.get('textarea[placeholder="现在实际发生了什么"]').element as HTMLTextAreaElement).value).toContain('执行到中间步骤时出现异常')

    await templateButtons[1].trigger('click')
    expect((wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').element as HTMLTextAreaElement).value).toContain('需要经过较多步骤')
    expect((wrapper.get('textarea[placeholder="希望系统如何表现"]').element as HTMLTextAreaElement).value).toContain('高频操作应更直接')
    expect((wrapper.get('textarea[placeholder="现在实际发生了什么"]').element as HTMLTextAreaElement).value).toContain('需要频繁滚动或切换视线')
    expect(wrapper.findAll('.quick-template-card--active')).toHaveLength(1)
  })

  it('clears quick template highlight after manual edits', async () => {
    apiGet.mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()

    const templateButtons = wrapper.findAll('.quick-template-card')
    await templateButtons[0].trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.quick-template-card--active')).toHaveLength(1)

    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('手动修改后的正文')
    await flushPromises()

    expect(wrapper.findAll('.quick-template-card--active')).toHaveLength(0)
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      page_url: expect.stringContaining('http'),
      page_title: 'Issue Intake',
      environment_context: expect.stringContaining('viewport='),
    })
    expect(wrapper.text()).toContain('提交成功，反馈编号 fb_001')
    expect(wrapper.text()).toContain('最近一次提交')
    expect(wrapper.text()).toContain('editor-copy-button')
  })

  it('hydrates editable context fields on mount', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()

    const urlInput = wrapper.get('input[placeholder="https://example.com/settings"]')
    const titleInput = wrapper.get('input[placeholder="反馈页面标题"]')
    const envTextarea = wrapper.get('textarea[placeholder="浏览器、系统、窗口尺寸或触发环境"]')

    expect((urlInput.element as HTMLInputElement).value).toContain('/intake')
    expect((urlInput.element as HTMLInputElement).value).not.toContain('?token=secret')
    expect((urlInput.element as HTMLInputElement).value).not.toContain('#composer')
    expect((titleInput.element as HTMLInputElement).value).toBe('Issue Intake')
    expect((envTextarea.element as HTMLTextAreaElement).value).toContain('viewport=')
    expect((envTextarea.element as HTMLTextAreaElement).value).not.toContain('ua=')
    expect(wrapper.text()).toContain('已带页面链接')
  })

  it('truncates default title and environment context on mount', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })
    document.title = 'T'.repeat(260)
    Object.defineProperty(window.navigator, 'platform', { value: 'P'.repeat(300), configurable: true })
    Object.defineProperty(window.navigator, 'language', { value: 'L'.repeat(120), configurable: true })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()

    const titleInput = wrapper.get('input[placeholder="反馈页面标题"]')
    const envTextarea = wrapper.get('textarea[placeholder="浏览器、系统、窗口尺寸或触发环境"]')

    expect((titleInput.element as HTMLInputElement).value).toHaveLength(200)
    expect((envTextarea.element as HTMLTextAreaElement).value.length).toBeLessThanOrEqual(500)
    expect((envTextarea.element as HTMLTextAreaElement).value).not.toContain('ua=')
  })

  it('sanitizes and truncates page url before submission', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })
    apiPost.mockResolvedValue({
      success: true,
      data: {
        id: 'fb_012',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('input[placeholder="https://example.com/settings"]').setValue(`https://app.example.com/${'segment-'.repeat(180)}?token=secret#composer`)
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    const submittedPayload = apiPost.mock.calls[0][1]
    expect(submittedPayload.page_url).toMatch(/^https:\/\/app\.example\.com\//)
    expect(submittedPayload.page_url).not.toContain('?token=secret')
    expect(submittedPayload.page_url).not.toContain('#composer')
    expect(submittedPayload.page_url.length).toBeLessThanOrEqual(1000)
  })

  it('preserves non-network page url schemes without query or hash mangling', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })
    apiPost.mockResolvedValue({
      success: true,
      data: {
        id: 'fb_014',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('input[placeholder="https://example.com/settings"]').setValue('mailto:support@example.com?subject=Help#draft')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    const submittedPayload = apiPost.mock.calls[0][1]
    expect(submittedPayload.page_url).toBe('mailto:support@example.com')
  })

  it('truncates page title and environment context before submission', async () => {
    apiGet.mockResolvedValue({ success: true, data: { items: [] } })
    apiPost.mockResolvedValue({
      success: true,
      data: {
        id: 'fb_013',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('input[placeholder="反馈页面标题"]').setValue('T'.repeat(260))
    await wrapper.get('textarea[placeholder="浏览器、系统、窗口尺寸或触发环境"]').setValue('E'.repeat(620))
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    const submittedPayload = apiPost.mock.calls[0][1]
    expect(submittedPayload.page_title).toHaveLength(200)
    expect(submittedPayload.environment_context.length).toBeLessThanOrEqual(500)
  })

  it('clears quick template highlight after successful submission reset', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
    apiPost.mockResolvedValue({
      success: true,
      data: {
        id: 'fb_011',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    const templateButtons = wrapper.findAll('.quick-template-card')
    await templateButtons[0].trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.findAll('.quick-template-card--active')).toHaveLength(0)
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
      data: {
        id: 'fb_010',
        status: 'pending',
        created_at: '2026-06-11T10:00:00Z',
      },
    })

    const wrapper = mount(UserHomePage, {
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
    expect(wrapper.findAll('.quick-template-card--active')).toHaveLength(0)
    vi.useRealTimers()
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
    })

    await flushPromises()
    await wrapper.get('button[role="radio"]').trigger('click')
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    const actionButtons = wrapper.findAll('.submission-summary-card button')
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
      global: {
        stubs: {
          AppShell: {
            template: '<div><slot /></div>',
          },
        },
      },
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
})
