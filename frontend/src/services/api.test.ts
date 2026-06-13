import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiGet, apiPost } from './api'

describe('api service', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        json: vi.fn().mockResolvedValue({ success: true, data: {} }),
      }),
    )
  })

  it('adds admin token header for admin requests', async () => {
    window.sessionStorage.setItem('issueAggregatorAdminToken', 'secret-token')

    await apiGet('/api/admin/workbench/feedback')

    expect(fetch).toHaveBeenCalledWith('/api/admin/workbench/feedback', {
      headers: {
        'X-Admin-Token': 'secret-token',
      },
    })
  })

  it('keeps public requests without admin token header', async () => {
    window.sessionStorage.setItem('issueAggregatorAdminToken', 'secret-token')

    await apiPost('/api/feedback', { raw_content: 'body' })

    expect(fetch).toHaveBeenCalledWith('/api/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ raw_content: 'body' }),
    })
  })

  it('does not attach admin token to similar public prefixes', async () => {
    window.sessionStorage.setItem('issueAggregatorAdminToken', 'secret-token')

    await apiGet('/api/admin/workbench-public/status')

    expect(fetch).toHaveBeenCalledWith('/api/admin/workbench-public/status', {
      headers: {},
    })
  })

  it('does not read admin token from bundled environment variables', async () => {
    await apiGet('/api/admin/workbench/feedback')

    expect(fetch).toHaveBeenCalledWith('/api/admin/workbench/feedback', {
      headers: {},
    })
  })

  it('returns a failure envelope when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.reject(new Error('offline'))))

    const response = await apiGet('/api/issues/submitted')

    expect(response.success).toBe(false)
    expect(response.error_code).toBe('NETWORK_ERROR')
  })

  it('returns a failure envelope for non-json responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: vi.fn().mockImplementation(() => Promise.reject(new SyntaxError('bad json'))),
      }),
    )

    const response = await apiGet('/api/issues/submitted')

    expect(response.success).toBe(false)
    expect(response.error_code).toBe('INVALID_API_RESPONSE')
    expect(response.message).toContain('HTTP 502')
  })
})
