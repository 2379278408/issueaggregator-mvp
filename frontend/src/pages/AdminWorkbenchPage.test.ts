import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiGet, apiPost, apiPut } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}))

import AdminWorkbenchPage from './AdminWorkbenchPage.vue'

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
  apiPut,
  buildAdminApiPath: (path: string) => `/api/admin/workbench${path}`,
  hasAdminToken: () => Boolean(window.sessionStorage.getItem('issueAggregatorAdminToken')),
  setAdminToken: (token: string) => window.sessionStorage.setItem('issueAggregatorAdminToken', token),
}))

function mountPage(options: { unlocked?: boolean } = { unlocked: true }) {
  if (options.unlocked !== false) {
    window.sessionStorage.setItem('issueAggregatorAdminToken', 'secret-token')
  }

  return mount(AdminWorkbenchPage, {
    global: {
      stubs: {
        AppShell: {
          template: '<div><slot /></div>',
        },
      },
    },
  })
}

function findButtonByText(wrapper: ReturnType<typeof mountPage>, text: string) {
  return wrapper.findAll('button').find((button) => button.text().includes(text))
}

describe('AdminWorkbenchPage', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
  })

  it('keeps admin data locked until a token is provided', async () => {
    const wrapper = mountPage({ unlocked: false })
    await flushPromises()

    expect(wrapper.text()).toContain('输入管理凭据')
    expect(wrapper.find('.admin-layout').exists()).toBe(false)
    expect(apiGet).not.toHaveBeenCalled()

    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    await wrapper.get('input[type="password"]').setValue('secret-token')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(window.sessionStorage.getItem('issueAggregatorAdminToken')).toBe('secret-token')
    expect(apiGet).toHaveBeenCalled()
  })

  it('loads feedback counts on mount', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', status: 'pending', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_2', type: 'bug', related_id: 'editor-copy-button', raw_content: 'two', status: 'grouped', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('待处理')
    expect(wrapper.text()).toContain('草稿中')
    expect(wrapper.text()).toContain('已发布')
    expect(wrapper.text()).toContain('one')
  })

  it('shows review decision guidance for mixed related ids and missing fields', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            { id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', expected_behavior: '', actual_behavior: '', status: 'pending', created_at: 'now' },
            { id: 'fb_2', type: 'feature', related_id: 'toolbar-shortcuts', raw_content: 'two', expected_behavior: 'want', actual_behavior: '', status: 'pending', created_at: 'now' },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mountPage()
    await flushPromises()

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)
    await flushPromises()

    expect(wrapper.text()).toContain('建议拆分主题')
    expect(wrapper.text()).toContain('缺失3')
  })

  it('creates batch and integrates draft', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', status: 'pending', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', status: 'grouped', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'draft_1',
          batch_id: 'batch_1',
          title: '[Bug] editor-copy-button',
          body_markdown: 'Summary',
          related_id_summary: 'editor-copy-button',
          status: 'draft_ready',
          updated_at: '2026-06-11T11:10:00Z',
        },
      })
    apiPost
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'batch_1',
          status: 'created',
          primary_related_id: 'editor-copy-button',
          related_id_count: 1,
          created_at: '2026-06-11T11:00:00Z',
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          batch_id: 'batch_1',
          draft_id: 'draft_1',
          status: 'draft_ready',
        },
      })

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.get('input[type="checkbox"]').setValue(true)
    await findButtonByText(wrapper, '创建批次')!.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, '生成草稿')!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/api/admin/workbench/draft-batches', {
      feedback_item_ids: ['fb_1'],
      confirm_mixed_related_ids: false,
    })
    expect(apiPost).toHaveBeenCalledWith('/api/admin/workbench/draft-batches/batch_1/integrate', {})
    expect(wrapper.text()).toContain('批次创建成功：batch_1')
    expect(wrapper.find('textarea').element.value).toContain('Summary')
    expect(wrapper.text()).toContain('Issue Draft')
    expect(wrapper.text()).toContain('待提交')
  }, 10000)

  it('submits loaded draft and shows submission result', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', status: 'pending', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', status: 'grouped', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'draft_1',
          batch_id: 'batch_1',
          title: '[Bug] editor-copy-button',
          body_markdown: 'Summary',
          related_id_summary: 'editor-copy-button',
          status: 'draft_ready',
          updated_at: '2026-06-11T11:10:00Z',
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
    apiPut.mockResolvedValue({
      success: true,
      data: {
        id: 'draft_1',
        status: 'draft_ready',
        updated_at: '2026-06-11T11:15:00Z',
      },
    })
    apiPost
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'batch_1',
          status: 'created',
          primary_related_id: 'editor-copy-button',
          related_id_count: 1,
          created_at: '2026-06-11T11:00:00Z',
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          batch_id: 'batch_1',
          draft_id: 'draft_1',
          status: 'draft_ready',
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          draft_id: 'draft_1',
          issue_number: 501,
          issue_url: 'https://github.com/org/repo/issues/501',
          related_id: 'editor-copy-button',
          submitted_at: '2026-06-11T11:20:00Z',
        },
      })

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.get('input[type="checkbox"]').setValue(true)
    await findButtonByText(wrapper, '创建批次')!.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, '生成草稿')!.trigger('click')
    await flushPromises()

    expect((wrapper.get('input.input').element as HTMLInputElement).value).toBe('[Bug] editor-copy-button')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Summary')

    await findButtonByText(wrapper, '提交 GitHub')!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/api/admin/workbench/drafts/draft_1/submit', {})
    expect(wrapper.text()).toContain('GitHub Issue #501')
    expect(wrapper.text()).toContain('Issue #501')
  })

  it('clears previous draft context when switching to grouped records', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', status: 'pending', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_2', type: 'bug', related_id: 'toolbar-shortcuts', raw_content: 'two', status: 'grouped', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_2', type: 'bug', related_id: 'toolbar-shortcuts', raw_content: 'two', status: 'grouped', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'draft_1',
          batch_id: 'batch_1',
          title: '[Bug] editor-copy-button',
          body_markdown: 'Summary',
          related_id_summary: 'editor-copy-button',
          status: 'draft_ready',
          updated_at: '2026-06-11T11:10:00Z',
        },
      })
    apiPost
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'batch_1',
          status: 'created',
          primary_related_id: 'editor-copy-button',
          related_id_count: 1,
          created_at: '2026-06-11T11:00:00Z',
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          batch_id: 'batch_1',
          draft_id: 'draft_1',
          status: 'draft_ready',
        },
      })

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.get('input[type="checkbox"]').setValue(true)
    await findButtonByText(wrapper, '创建批次')!.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, '生成草稿')!.trigger('click')
    await flushPromises()

    await findButtonByText(wrapper, '草稿中')!.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('toolbar-shortcuts'))!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('当前参考记录')
    expect(findButtonByText(wrapper, '生成草稿')!.attributes('disabled')).toBeDefined()
    expect(findButtonByText(wrapper, '提交 GitHub')!.attributes('disabled')).toBeDefined()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toContain('用户信号数量')
  })
})
