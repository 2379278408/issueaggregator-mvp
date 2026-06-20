/* eslint-disable no-console */
import process from 'node:process'

import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')

const workbenchUrl = (process.env.ADMIN_E2E_URL || '').trim()
const username = (process.env.ADMIN_E2E_USERNAME || 'admin').trim()
const password = (process.env.ADMIN_E2E_PASSWORD || 'admin').trim()
const shouldSubmit = /^(1|true|yes)$/i.test((process.env.ADMIN_E2E_SUBMIT || '').trim())
const screenshotPath = (process.env.ADMIN_E2E_SCREENSHOT || '/tmp/opencode/admin-workbench-e2e.png').trim()

if (!workbenchUrl) {
  throw new Error('缺少 ADMIN_E2E_URL')
}

const workbench = new URL(workbenchUrl)
const apiOrigin = workbench.origin
const relatedId = `admin-e2e-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
const seededItems = [
  {
    type: 'bug',
    related_id: relatedId,
    raw_content: `${relatedId} first signal`,
    expected_behavior: 'expected behavior one',
    actual_behavior: 'actual behavior one',
  },
  {
    type: 'bug',
    related_id: relatedId,
    raw_content: `${relatedId} second signal`,
    expected_behavior: 'expected behavior two',
    actual_behavior: 'actual behavior two',
  },
]

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function seedFeedback(item) {
  const response = await fetch(`${apiOrigin}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  })
  const payload = await response.json().catch(() => null)
  if (response.status === 429 || payload?.error_code === 'FEEDBACK_DAILY_IP_LIMIT_REACHED') {
    return { limited: true, id: null }
  }
  if (!response.ok || !payload?.success) {
    throw new Error(`反馈注入失败: ${response.status}`)
  }
  return { limited: false, id: payload.data.id }
}

async function waitForQueueCards(page, text, expectedCount) {
  const cards = page.locator('.signal-card').filter({ hasText: text })
  await page.waitForFunction(
    ({ selector, textValue, count }) => {
      return (
        Array.from(document.querySelectorAll(selector)).filter((node) => node.textContent?.includes(textValue))
          .length >= count
      )
    },
    { selector: '.signal-card', textValue: text, count: expectedCount },
    { timeout: 60000 },
  )
  return cards
}

async function main() {
  for (const item of seededItems) {
    await seedFeedback(item)
  }

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })

  try {
    await page.goto(workbenchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {})
    await page.getByLabel('用户名').fill(username)
    await page.getByLabel('密码').fill(password)
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForSelector('.triage-grid', { timeout: 60000 })

    const cards = await waitForQueueCards(page, relatedId, 2)
    assert((await cards.count()) >= 2, '未在待整理队列中找到注入反馈')
    await cards.nth(0).locator('input[type="checkbox"]').check({ force: true })
    await cards.nth(1).locator('input[type="checkbox"]').check({ force: true })

    const batchBtn = page.getByRole('button').filter({ hasText: /创建批次|确认建批/ })
    await batchBtn.first().click()
    await page.waitForFunction(() => document.body.textContent?.includes('批次创建成功') || false, undefined, {
      timeout: 60000,
    })

    await page.getByRole('button', { name: '生成草稿' }).click()
    await page.waitForFunction(
      () => {
        const value = document.querySelector('#draft-panel textarea')?.value || ''
        return value.trim().length > 0 && !value.includes('用户信号数量')
      },
      undefined,
      { timeout: 60000 },
    )

    const titleInput = page.locator('#draft-panel .issue-title-field .input')
    const bodyInput = page.locator('#draft-panel .textarea--editor')
    await titleInput.fill(`[E2E] ${relatedId}`)
    await bodyInput.fill(`## 摘要\n${relatedId} browser flow\n\n## 验证\n建批、生成草稿、保存状态均通过。`)
    await page.getByRole('button', { name: '保存草稿' }).click()
    await page.waitForFunction(
      () => document.querySelector('.draft-sync-card strong')?.textContent?.includes('草稿已保存') || false,
      undefined,
      { timeout: 60000 },
    )

    let submitResult = null
    if (shouldSubmit) {
      await page.getByRole('button', { name: '提交 GitHub' }).click()
      await page.waitForFunction(
        () => document.querySelector('.draft-sync-card strong')?.textContent?.includes('GitHub 提交完成') || false,
        undefined,
        { timeout: 60000 },
      )
      submitResult = await page.locator('.submission-card--result').textContent()
    }

    const summary = await page.evaluate(() => ({
      reviewHeight: document.querySelector('#review-panel')?.getBoundingClientRect().height || null,
      draftHeight: document.querySelector('#draft-panel')?.getBoundingClientRect().height || null,
      syncLabel: document.querySelector('.draft-sync-card strong')?.textContent?.trim() || null,
      syncHint: document.querySelector('.draft-sync-card p')?.textContent?.trim() || null,
      batchMessage: document.querySelector('.draft-message, .feedback-message')?.textContent?.trim() || null,
    }))

    await page.screenshot({ path: screenshotPath, fullPage: true })
    const report = {
      ok: true,
      relatedId,
      submitExecuted: shouldSubmit,
      submitResult,
      screenshotPath,
      summary,
      teardown: {
        message: '后端 append-only，测试数据不会自动删除',
        identifyBy: `related_id = '${relatedId}'`,
      },
    }
    console.log(JSON.stringify(report, null, 2))
    console.log('')
    console.log('--- Teardown ---')
    console.log(`  标记: ${relatedId}`)
    console.log('  说明: 后端 append-only，数据不会自动删除')
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error)
  process.exit(1)
})
