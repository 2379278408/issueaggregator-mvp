import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiGet, apiPost, apiPut } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}))

const { adminLogin, adminLogout, adminSessionMe } = vi.hoisted(() => ({
  adminLogin: vi.fn(),
  adminLogout: vi.fn(),
  adminSessionMe: vi.fn(),
}))

const { routeQuery, routerReplace } = vi.hoisted(() => ({
  routeQuery: {} as Record<string, string>,
  routerReplace: vi.fn(),
}))

import AdminWorkbenchPage from './AdminWorkbenchPage.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routeQuery }),
  useRouter: () => ({ replace: routerReplace }),
}))

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
  apiPut,
  adminLogin,
  adminLogout,
  adminSessionMe,
  buildAdminApiPath: (path: string) => `/api/admin/workbench${path}`,
  clearAdminToken: () => window.sessionStorage.removeItem('issueAggregatorAdminToken'),
  hasAdminToken: () => Boolean(window.sessionStorage.getItem('issueAggregatorAdminToken')),
  setAdminToken: (token: string) => window.sessionStorage.setItem('issueAggregatorAdminToken', token),
}))

function mountPage(options: { unlocked?: boolean } = { unlocked: true }) {
  if (options.unlocked !== false) {
    window.sessionStorage.setItem('issueAggregatorAdminToken', 'session-active')
    adminSessionMe.mockResolvedValue({
      success: true,
      data: {
        authenticated: true,
        username: 'admin',
        session_expires_at: '2030-01-01T00:00:00Z',
        idle_expires_at: '2030-01-01T00:00:00Z',
      },
    })
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
    adminLogin.mockReset()
    adminLogout.mockReset()
    adminSessionMe.mockReset()
    routerReplace.mockReset()
    Object.keys(routeQuery).forEach((key) => delete routeQuery[key])
    apiGet.mockResolvedValue({ success: true, data: { items: [], page: 1, page_size: 20, total: 0 } })
    adminSessionMe.mockResolvedValue({
      success: true,
      data: { authenticated: false, username: null, session_expires_at: null, idle_expires_at: null },
    })
  })

  it('keeps admin data locked until login succeeds', async () => {
    const wrapper = mountPage({ unlocked: false })
    await flushPromises()

    expect(wrapper.text()).toContain('管理员登录')
    expect(wrapper.find('.admin-layout').exists()).toBe(false)
    expect(apiGet).not.toHaveBeenCalled()

    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
    adminLogin.mockResolvedValueOnce({
      success: true,
      data: { username: 'admin', session_expires_at: '2030-01-01T00:00:00Z', idle_expires_at: '2030-01-01T00:00:00Z' },
    })

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin')
    await inputs[1].setValue('password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(window.sessionStorage.getItem('issueAggregatorAdminToken')).toBe('session-active')
    expect(apiGet).toHaveBeenCalled()
  })

  it('returns to the login form when login fails', async () => {
    apiGet.mockResolvedValue({ success: false, message: 'invalid token', http_status: 401 })
    adminLogin.mockResolvedValue({ success: false, message: '用户名或密码错误。' })

    const wrapper = mountPage({ unlocked: false })
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin')
    await inputs[1].setValue('wrong')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('用户名或密码错误。')
    expect(wrapper.text()).toContain('管理员登录')
    expect(window.sessionStorage.getItem('issueAggregatorAdminToken')).toBeNull()
  })

  it('shows the cooldown message when admin login is temporarily blocked', async () => {
    adminLogin.mockResolvedValue({
      success: false,
      error_code: 'ADMIN_LOGIN_COOLDOWN_ACTIVE',
      message: '登录冷却中，请 29m 59s 后再试。',
    })

    const wrapper = mountPage({ unlocked: false })
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin')
    await inputs[1].setValue('wrong')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('登录冷却中，请 29m 59s 后再试。')
    expect(wrapper.text()).toContain('管理员登录')
  })

  it('loads feedback counts on mount', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('待处理')
    expect(wrapper.text()).toContain('草稿中')
    expect(wrapper.text()).toContain('已发布')
    expect(wrapper.text()).toContain('one')
  })

  it('renders recent audit events in the admin workspace', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'audit_1',
              event_type: 'admin_action_succeeded',
              client_ip: '8.8.8.8',
              path: '/api/admin/workbench/draft-batches',
              action: 'create_draft_batch',
              resource_id: 'batch_1',
              created_at: '2026-06-13T14:00:00Z',
            },
          ],
          total: 1,
        },
      })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('最近审计事件')
    expect(wrapper.text()).toContain('管理员操作成功 · create_draft_batch')
    expect(wrapper.text()).toContain('batch_1')
  })

  it('filters audit events by event type', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'audit_2',
              event_type: 'admin_auth_failed',
              client_ip: '8.8.8.8',
              path: '/api/admin/workbench/feedback',
              action: null,
              resource_id: null,
              created_at: '2026-06-13T14:00:00Z',
            },
          ],
          total: 1,
        },
      })

    const wrapper = mountPage()
    await flushPromises()

    await findButtonByText(wrapper, '鉴权失败')!.trigger('click')
    await flushPromises()

    expect(apiGet).toHaveBeenLastCalledWith(
      '/api/admin/workbench/audit-events?page_size=8&event_type=admin_auth_failed',
    )
    expect(routerReplace).toHaveBeenLastCalledWith({ query: { auditEventType: 'admin_auth_failed' } })
    expect(wrapper.text()).toContain('管理员鉴权失败')
  })

  it('filters audit events by keyword', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'audit_3',
              event_type: 'admin_action_succeeded',
              client_ip: '8.8.4.4',
              path: '/api/admin/workbench/draft-batches',
              action: 'create_draft_batch',
              resource_id: 'batch_123',
              created_at: '2026-06-13T14:00:00Z',
            },
          ],
          total: 1,
        },
      })

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.get('input[placeholder="按 IP、路径、动作或资源检索"]').setValue('batch_123')
    await findButtonByText(wrapper, '检索')!.trigger('click')
    await flushPromises()

    expect(apiGet).toHaveBeenLastCalledWith('/api/admin/workbench/audit-events?page_size=8&keyword=batch_123')
    expect(routerReplace).toHaveBeenLastCalledWith({ query: { auditKeyword: 'batch_123' } })
    expect(wrapper.text()).toContain('batch_123')
  })

  it('filters audit events by time range', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })

    const wrapper = mountPage()
    await flushPromises()

    await findButtonByText(wrapper, '1 小时')!.trigger('click')
    await flushPromises()

    expect(apiGet).toHaveBeenLastCalledWith('/api/admin/workbench/audit-events?page_size=8&time_range=1h')
    expect(routerReplace).toHaveBeenLastCalledWith({ query: { auditTimeRange: '1h' } })
  })

  it('restores audit filters from route query on mount', async () => {
    routeQuery.auditEventType = 'admin_action_succeeded'
    routeQuery.auditTimeRange = '24h'
    routeQuery.auditKeyword = 'batch_9'
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })

    const wrapper = mountPage()
    await flushPromises()

    expect(apiGet).toHaveBeenLastCalledWith(
      '/api/admin/workbench/audit-events?page_size=8&event_type=admin_action_succeeded&time_range=24h&keyword=batch_9',
    )
    expect((wrapper.get('input[placeholder="按 IP、路径、动作或资源检索"]').element as HTMLInputElement).value).toBe(
      'batch_9',
    )
  })

  it('restores grouped draft context from route query on mount', async () => {
    routeQuery.adminQueue = 'grouped'
    routeQuery.batchId = 'batch_1'
    routeQuery.draftId = 'draft_1'
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_1',
              draft_id: 'draft_1',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'draft_1',
          batch_id: 'batch_1',
          title: '[问题] editor-copy-button',
          body_markdown: 'Summary',
          related_id_summary: 'editor-copy-button',
          status: 'draft_ready',
          updated_at: '2026-06-11T11:10:00Z',
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })

    const wrapper = mountPage()
    await flushPromises()

    expect(apiGet).toHaveBeenCalledWith('/api/admin/workbench/drafts/draft_1')
    expect(wrapper.text()).toContain('草稿中')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toContain('Summary')
    expect(routerReplace).toHaveBeenLastCalledWith({
      query: { adminQueue: 'grouped', batchId: 'batch_1', draftId: 'draft_1' },
    })
  })

  it('drops invalid batch and draft query context after loading', async () => {
    routeQuery.adminQueue = 'grouped'
    routeQuery.batchId = 'batch_missing'
    routeQuery.draftId = 'draft_missing'
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })

    mountPage()
    await flushPromises()

    expect(routerReplace).toHaveBeenLastCalledWith({ query: { adminQueue: 'grouped' } })
  })

  it('returns to the login form when stored admin session is rejected', async () => {
    apiGet.mockResolvedValue({ success: false, message: 'invalid token', http_status: 401 })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('登录态已失效，请重新登录。')
    expect(wrapper.text()).toContain('管理员登录')
    expect(wrapper.text()).not.toContain('正在加载')
  })

  it('keeps the admin session when initial data loading fails temporarily', async () => {
    apiGet.mockResolvedValue({ success: false, message: 'network down', http_status: 502 })

    const wrapper = mountPage()
    await flushPromises()

    expect(window.sessionStorage.getItem('issueAggregatorAdminToken')).toBe('session-active')
    expect(wrapper.text()).toContain('管理数据加载失败，请检查后端服务。')
    expect(wrapper.text()).toContain('整理反馈，生成 Issue')
  })

  it('returns to the login form after logout', async () => {
    routeQuery.adminQueue = 'grouped'
    routeQuery.batchId = 'batch_1'
    routeQuery.draftId = 'draft_1'
    routeQuery.auditEventType = 'admin_auth_failed'
    routeQuery.auditTimeRange = '24h'
    routeQuery.auditKeyword = 'batch_1'
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
    adminLogout.mockResolvedValue({ success: true, data: { status: 'logged_out' } })

    const wrapper = mountPage()
    await flushPromises()

    await findButtonByText(wrapper, '登出')!.trigger('click')
    await flushPromises()

    expect(adminLogout).toHaveBeenCalledTimes(1)
    expect(window.sessionStorage.getItem('issueAggregatorAdminToken')).toBeNull()
    expect(wrapper.text()).toContain('管理员登录')
    expect(routerReplace).toHaveBeenLastCalledWith({ query: {} })
  })

  it('clears stale queue data when a later admin refresh fails', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: false, message: 'network down' })
      .mockResolvedValueOnce({ success: false, message: 'network down' })
      .mockResolvedValueOnce({ success: false, message: 'network down' })
    apiPost.mockResolvedValueOnce({
      success: true,
      data: {
        id: 'batch_1',
        status: 'created',
        primary_related_id: 'editor-copy-button',
        related_id_count: 1,
        created_at: '2026-06-11T11:00:00Z',
      },
    })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('one')
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await findButtonByText(wrapper, '创建批次')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('管理数据加载失败')
    expect(wrapper.text()).not.toContain('one')
    expect(wrapper.text()).toContain('当前队列为空')
    expect(wrapper.text()).toContain('batch_1')
    expect(findButtonByText(wrapper, '生成草稿')!.attributes('disabled')).toBeUndefined()
  })

  it('shows review decision guidance for mixed related ids and missing fields', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              expected_behavior: '',
              actual_behavior: '',
              status: 'pending',
              created_at: 'now',
            },
            {
              id: 'fb_2',
              type: 'feature',
              related_id: 'toolbar-shortcuts',
              raw_content: 'two',
              expected_behavior: 'want',
              actual_behavior: '',
              status: 'pending',
              created_at: 'now',
            },
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
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'grouped',
              created_at: 'now',
            },
          ],
        },
      })
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
    expect(wrapper.text()).toContain('当前草稿可直接继续完善')
  }, 10000)

  it('keeps grouped batch context after creating a multi-feedback batch', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'two',
              status: 'pending',
              created_at: 'now',
            },
            {
              id: 'fb_3',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'three',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_multi',
            },
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_multi',
            },
            {
              id: 'fb_3',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'three',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_multi',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
    apiPost.mockResolvedValueOnce({
      success: true,
      data: {
        id: 'batch_multi',
        status: 'created',
        primary_related_id: 'editor-copy-button',
        related_id_count: 1,
        created_at: '2026-06-11T11:00:00Z',
      },
    })

    const wrapper = mountPage()
    await flushPromises()

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    await checkboxes[0].setValue(true)
    await checkboxes[1].setValue(true)
    await checkboxes[2].setValue(true)
    await findButtonByText(wrapper, '创建批次')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('当前批次反馈')
    expect(wrapper.text()).toContain('当前批次共包含 3 条反馈')
    expect(wrapper.text()).toContain('one')
    expect(wrapper.text()).toContain('two')
    expect(wrapper.text()).toContain('three')
    expect(routerReplace).toHaveBeenLastCalledWith({ query: { adminQueue: 'grouped', batchId: 'batch_multi' } })
  })

  it('shows batch summary cards and pre-submit checklist for a loaded draft', async () => {
    routeQuery.adminQueue = 'grouped'
    routeQuery.batchId = 'batch_1'
    routeQuery.draftId = 'draft_1'
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_1',
              draft_id: 'draft_1',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'draft_1',
          batch_id: 'batch_1',
          title: '[问题] editor-copy-button',
          body_markdown: '## 摘要\n内容\n## 影响\n更多内容',
          related_id_summary: 'editor-copy-button',
          status: 'draft_ready',
          updated_at: '2026-06-11T11:10:00Z',
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })

    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('批次条目数')
    expect(wrapper.text()).toContain('关联标识数')
    expect(wrapper.text()).toContain('提交前确认')
    expect(wrapper.text()).toContain('标题 23 字')
    expect(wrapper.text()).toContain('2 个 Markdown 小节')
  })

  it('recovers when batch creation rejects', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
    apiPost.mockRejectedValue(new Error('network down'))

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.get('input[type="checkbox"]').setValue(true)
    await findButtonByText(wrapper, '创建批次')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('批次创建失败，请检查网络后重试')
    expect(findButtonByText(wrapper, '创建批次')!.attributes('disabled')).toBeUndefined()
  })

  it('selects all pending feedback with one action', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'two',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })

    const wrapper = mountPage()
    await flushPromises()

    await findButtonByText(wrapper, '一键勾选')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('已选 2 / 2')
    expect(
      wrapper.findAll('input[type="checkbox"]').every((checkbox) => (checkbox.element as HTMLInputElement).checked),
    ).toBe(true)
  }, 10000)

  it('resumes a failed grouped batch and regenerates a draft', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_failed',
              batch_status: 'failed',
              batch_integration_error: 'AI API request timed out',
              draft_id: null,
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          id: 'draft_1',
          batch_id: 'batch_failed',
          title: '[Bug] editor-copy-button',
          body_markdown: 'Summary',
          related_id_summary: 'editor-copy-button',
          status: 'draft_ready',
          updated_at: '2026-06-11T11:10:00Z',
        },
      })
    apiPost.mockResolvedValueOnce({
      success: true,
      data: {
        batch_id: 'batch_failed',
        draft_id: 'draft_1',
        status: 'draft_ready',
      },
    })

    const wrapper = mountPage()
    await flushPromises()

    await findButtonByText(wrapper, '草稿中')!.trigger('click')
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('editor-copy-button'))!
      .trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('上次生成失败')
    await findButtonByText(wrapper, '生成草稿')!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/api/admin/workbench/draft-batches/batch_failed/integrate', {})
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toContain('Summary')
  })

  it('submits loaded draft and shows submission result', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'grouped',
              created_at: 'now',
            },
          ],
        },
      })
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
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'toolbar-shortcuts',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'toolbar-shortcuts',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
            },
          ],
        },
      })
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
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('toolbar-shortcuts'))!
      .trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('当前批次反馈')
    expect(findButtonByText(wrapper, '生成草稿')!.attributes('disabled')).toBeDefined()
    expect(findButtonByText(wrapper, '提交 GitHub')!.attributes('disabled')).toBeDefined()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toContain('用户信号数量')
  })

  it('restores unsaved local draft edits after switching away and back', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_1',
              draft_id: 'draft_1',
            },
            {
              id: 'fb_3',
              type: 'bug',
              related_id: 'toolbar-shortcuts',
              raw_content: 'three',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_2',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [],
          total: 0,
        },
      })
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

    const wrapper = mountPage()
    await flushPromises()

    await findButtonByText(wrapper, '草稿中')!.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('editor-copy-button'))!.trigger('click')
    await flushPromises()

    await wrapper.get('textarea').setValue('Summary\n\nLocal unsaved change')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('toolbar-shortcuts'))!.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('editor-copy-button'))!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('已恢复本地未保存改动')
    expect(wrapper.text()).toContain('存在未保存改动')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toContain('Local unsaved change')
  })

  it('switches to submitted queue after GitHub submission succeeds', async () => {
    apiGet
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'pending',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_1',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'one',
              status: 'grouped',
              created_at: 'now',
              batch_id: 'batch_1',
              draft_id: 'draft_1',
            },
          ],
        },
      })
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
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_9',
              type: 'bug',
              related_id: 'editor-copy-button',
              raw_content: 'submitted',
              status: 'submitted',
              created_at: 'now',
              batch_id: 'batch_1',
              draft_id: 'draft_1',
            },
          ],
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
    await findButtonByText(wrapper, '提交 GitHub')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('GitHub 提交完成')
    expect(wrapper.text()).toContain('已发布')
    expect(routerReplace).toHaveBeenLastCalledWith({ query: { adminQueue: 'submitted', batchId: 'batch_1', draftId: 'draft_1' } })
  })

  it('syncs queue context to route when switching status', async () => {
    apiGet
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({
        success: true,
        data: {
          items: [
            {
              id: 'fb_2',
              type: 'bug',
              related_id: 'toolbar-shortcuts',
              raw_content: 'two',
              status: 'grouped',
              created_at: 'now',
            },
          ],
        },
      })
      .mockResolvedValueOnce({ success: true, data: { items: [] } })
      .mockResolvedValueOnce({ success: true, data: { items: [], total: 0 } })

    const wrapper = mountPage()
    await flushPromises()

    await findButtonByText(wrapper, '草稿中')!.trigger('click')
    await flushPromises()

    expect(routerReplace).toHaveBeenLastCalledWith({ query: { adminQueue: 'grouped' } })
  })
})
