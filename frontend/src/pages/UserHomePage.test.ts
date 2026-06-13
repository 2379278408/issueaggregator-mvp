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
    return '/portal/issues/submitted'
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
    apiGet.mockReset()
    apiPost.mockReset()
    buildPublicApiPath.mockClear()
    buildSubmittedIssueSearch.mockClear()
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
    await wrapper.get('button.button--secondary').trigger('click')
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

    expect(wrapper.text()).toContain('发现同主题')
    expect(wrapper.text()).toContain('Duplicate issue')
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
    expect(apiGet).toHaveBeenLastCalledWith('/portal/issues/submitted/search?related_id=github-submit-flow')
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
    expect(apiGet).toHaveBeenCalledTimes(1)
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
    expect(apiGet).toHaveBeenLastCalledWith('/portal/issues/submitted/search?related_id=github-submit-flow')
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
    })
    expect(wrapper.text()).toContain('提交成功，反馈编号 fb_001')
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
