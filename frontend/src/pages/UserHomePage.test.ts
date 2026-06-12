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
    expect(wrapper.text()).toContain('Existing issue')
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
    await wrapper.get('input[placeholder="editor-copy-button"]').setValue('editor-copy-button')
    await wrapper.get('textarea[placeholder="描述触发场景、具体表现和影响范围"]').setValue('feedback body')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(apiPost).toHaveBeenCalled()
    expect(apiPost.mock.calls[0][0]).toBe('/portal/feedback')
    expect(apiPost.mock.calls[0][1]).toMatchObject({
      related_id: 'editor-copy-button',
      raw_content: 'feedback body',
    })
  })
})
