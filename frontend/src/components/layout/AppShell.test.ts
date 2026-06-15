import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AppShell from './AppShell.vue'

describe('AppShell', () => {
  it('does not expose the admin route in public navigation', () => {
    const wrapper = mount(AppShell, {
      props: {
        title: 'Issue Aggregator',
        description: '用户反馈入口',
      },
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    expect(wrapper.text()).toContain('用户提交页')
    expect(wrapper.text()).not.toContain('管理员工作台')
    expect(wrapper.findAllComponents(RouterLinkStub).map((link) => link.props('to'))).toEqual(['/'])
  })

  it('applies the wide shell modifier when requested', () => {
    const wrapper = mount(AppShell, {
      props: {
        title: 'Issue Triage Studio',
        description: '后台工作区',
        wide: true,
      },
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    })

    expect(wrapper.get('.page-shell').classes()).toContain('page-shell--wide')
  })
})
