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
})
