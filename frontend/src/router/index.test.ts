import { afterEach, describe, expect, it, vi } from 'vitest'

describe('router config', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('registers the configured admin slug', async () => {
    vi.stubEnv('VITE_ADMIN_ROUTE_SLUG', 'secretpanel')

    const { default: router } = await import('./index')
    const adminRoute = router.getRoutes().find((route) => route.name === 'admin-workbench')

    expect(adminRoute?.path).toBe('/secretpanel')
  })

  it('does not keep the legacy /admin route', async () => {
    vi.stubEnv('VITE_ADMIN_ROUTE_SLUG', 'secretpanel')

    const { default: router } = await import('./index')
    const legacyRoute = router.getRoutes().find((route) => route.path === '/admin')

    expect(legacyRoute).toBeUndefined()
  })
})
