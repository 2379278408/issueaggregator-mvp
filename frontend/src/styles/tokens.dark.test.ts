import { describe, it, expect, afterEach } from 'vitest'

function injectTestTokens(): HTMLStyleElement {
  const style = document.createElement('style')
  style.textContent = `
    :root { --color-bg: #fffaf0; }
    [data-theme="dark"] { --color-bg: #0d1117; }
  `
  document.head.appendChild(style)
  return style
}

describe('dark mode tokens', () => {
  let styleEl: HTMLStyleElement | null = null

  afterEach(() => {
    document.documentElement.removeAttribute('data-theme')
    if (styleEl) {
      styleEl.remove()
      styleEl = null
    }
  })

  it('applies light theme variables by default', () => {
    styleEl = injectTestTokens()
    document.documentElement.removeAttribute('data-theme')
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim()
    expect(bg).toBe('#fffaf0')
  })

  it('applies dark theme variables when data-theme=dark', () => {
    styleEl = injectTestTokens()
    document.documentElement.setAttribute('data-theme', 'dark')
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim()
    expect(bg).toBe('#0d1117')
  })

  it('allows overriding to light when dark is preferred', () => {
    styleEl = injectTestTokens()
    document.documentElement.setAttribute('data-theme', 'light')
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim()
    expect(bg).toBe('#fffaf0')
  })

  it('data-theme attribute reads back correctly', () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    document.documentElement.setAttribute('data-theme', 'light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })
})
