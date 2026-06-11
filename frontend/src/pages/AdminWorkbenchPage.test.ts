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
}))

function mountPage() {
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
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
  })

  it('loads feedback counts on mount', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_1', type: 'bug', related_id: 'editor-copy-button', raw_content: 'one', status: 'pending', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [{ id: 'fb_2', type: 'bug', related_id: 'editor-copy-button', raw_content: 'two', status: 'grouped', created_at: 'now' }] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('Pending')
    expect(wrapper.text()).toContain('Grouped')
    expect(wrapper.text()).toContain('Submitted')
    expect(wrapper.text()).toContain('one')
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
    await findButtonByText(wrapper, '生成 Draft')!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/api/draft-batches', {
      feedback_item_ids: ['fb_1'],
      confirm_mixed_related_ids: false,
    })
    expect(apiPost).toHaveBeenCalledWith('/api/draft-batches/batch_1/integrate', {})
    expect(wrapper.text()).toContain('批次创建成功：batch_1')
    expect(wrapper.find('textarea').element.value).toContain('Summary')
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
    await findButtonByText(wrapper, '生成 Draft')!.trigger('click')
    await flushPromises()

    expect((wrapper.get('input.input').element as HTMLInputElement).value).toBe('[Bug] editor-copy-button')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Summary')

    await findButtonByText(wrapper, '提交到 GitHub')!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/api/drafts/draft_1/submit', {})
    expect(wrapper.text()).toContain('Issue #501')
  })
})
