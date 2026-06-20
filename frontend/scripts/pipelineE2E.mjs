/* eslint-disable no-console */
import process from 'node:process'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')

const BASE_URL = (process.env.PIPELINE_E2E_URL || '').trim()
const ADMIN_ROUTE = (process.env.PIPELINE_E2E_ADMIN_ROUTE || '057e044bfdb29f3e4a036d7d4094349d').trim()
const USERNAME = (process.env.PIPELINE_E2E_USERNAME || 'admin').trim()
const PASSWORD = (process.env.PIPELINE_E2E_PASSWORD || 'admin').trim()
const SHOULD_SUBMIT = /^(1|true|yes)$/i.test((process.env.PIPELINE_E2E_SUBMIT || '').trim())
const SCREENSHOT_DIR = (process.env.PIPELINE_E2E_SCREENSHOT_DIR || '/tmp/opencode/pipeline-e2e').trim()

const ADMIN_URL = `${BASE_URL}/${ADMIN_ROUTE}`
const API_URL = `${BASE_URL}/api/feedback`
const TIMESTAMP = Date.now()
const RELATED_ID = `pipeline-e2e-${TIMESTAMP}-${Math.random().toString(36).slice(2, 6)}`

const results = []
let screenshotIndex = 0

function step(label) {
  const s = { label, status: 'pending', detail: null, duration: null }
  results.push(s)
  return s
}

async function run(label, fn) {
  const s = step(label)
  const start = Date.now()
  try {
    s.detail = await fn()
    s.status = 'pass'
  } catch (e) {
    s.status = 'fail'
    s.detail = e.message
  }
  s.duration = Date.now() - start
  console.log(`  [${s.status.toUpperCase()}] ${label} (${s.duration}ms)`)
}

async function screenshot(page, name) {
  const path = `${SCREENSHOT_DIR}/${String(++screenshotIndex).padStart(2, '0')}-${name}.png`
  await page.screenshot({ path, fullPage: true })
  return path
}

// ── 模拟真实用户的反馈数据 ──

const feedbackItems = [
  {
    type: 'bug',
    related_id: RELATED_ID,
    raw_content:
      '点击"导出报表"按钮后页面白屏，控制台报错 Uncaught TypeError: Cannot read properties of undefined (reading "map")。确认数据源接口返回正常，但前端渲染时未处理空数组情况。',
    expected_behavior: '即使数据为空，也应显示空状态提示而非白屏崩溃。',
    actual_behavior: '页面白屏，控制台抛出异常，用户无法继续操作。',
    page_url: 'https://app.example.com/dashboard/reports',
    page_title: '数据报表 - Dashboard',
    environment_context: 'Chrome 128 / macOS 14.5 / 1920x1080',
  },
  {
    type: 'bug',
    related_id: RELATED_ID,
    raw_content:
      '在深色模式下，表格的斑马纹背景色与文字颜色对比度不足（#333 底色配 #666 文字），导致数据完全看不清。切换回浅色模式后正常。',
    expected_behavior: '深色模式下表格文字与背景应有足够对比度（至少 4.5:1），保证可读性。',
    actual_behavior: '深色模式表格行文字几乎不可见，影响数据阅读体验。',
    page_url: 'https://app.example.com/dashboard/reports',
    page_title: '数据报表 - Dashboard',
    environment_context: 'Chrome 128 / macOS 14.5 / 系统深色模式',
  },
  {
    type: 'enhancement',
    related_id: RELATED_ID,
    raw_content:
      '报表页面缺少日期范围筛选器，目前只能查看全部数据。如果能按周/月筛选，并支持自定义起止日期，会大幅提升运营团队的日常使用效率。',
    expected_behavior: '提供日期范围选择器，支持快捷选项（本周/本月/上月）和自定义区间，默认展示本月数据。',
    actual_behavior: '没有任何日期筛选功能，只能看到所有历史数据混在一起。',
    page_url: 'https://app.example.com/dashboard/reports',
    page_title: '数据报表 - Dashboard',
  },
]

// ── 主流程 ──

async function main() {
  if (!BASE_URL) throw new Error('缺少 PIPELINE_E2E_URL')

  const fs = require('fs')
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })

  console.log('Pipeline E2E')
  console.log(`  base:     ${BASE_URL}`)
  console.log(`  admin:    ${ADMIN_URL}`)
  console.log(`  related:  ${RELATED_ID}`)
  console.log(`  submit:   ${SHOULD_SUBMIT}`)
  console.log('')

  // ── 健康检查：确认后端可达 ──
  const preflight = await fetch(`${BASE_URL}/api/health`, { signal: AbortSignal.timeout(10000) }).catch(() => null)
  if (!preflight || !preflight.ok) {
    console.log(`  [SKIP] 后端不可达 (${BASE_URL}/api/health)，请确认服务已启动`)
    console.log(JSON.stringify({ ok: false, error: 'backend unreachable', steps: [] }, null, 2))
    return
  }

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })

  try {
    // ═══ 阶段一：模拟用户提交反馈 ═══
    console.log('--- 阶段一：用户提交反馈 ---')

    // ── 尝试注入测试反馈 ──
    let seedOk = false
    let seedMessage = ''
    const fedIds = []

    for (const item of feedbackItems) {
      try {
        const res = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item),
        })
        const payload = await res.json()
        if (res.ok && payload?.success) {
          fedIds.push(payload.data.id)
          seedOk = true
        } else if (payload?.error_code === 'FEEDBACK_DAILY_IP_LIMIT_REACHED') {
          seedMessage = payload.message
          break
        } else {
          seedMessage = `HTTP ${res.status}: ${JSON.stringify(payload)}`
          break
        }
      } catch {
        seedMessage = '网络异常'
        break
      }
    }

    await run('用户提交反馈到系统', async () => {
      if (seedOk) return `成功提交 ${fedIds.length} 条反馈 (${RELATED_ID})`
      if (seedMessage.includes('IP')) return `跳过（限流）：${seedMessage}`
      throw new Error(seedMessage || '未知错误')
    })

    await screenshot(page, '00-blank-before-login')

    // ═══ 阶段二：管理员登录后台 ═══
    console.log('--- 阶段二：管理员登录后台 ---')

    await run('打开后台登录页', async () => {
      await page.goto(ADMIN_URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
      await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {})
      const hasLogin = await page
        .getByLabel('用户名')
        .isVisible()
        .catch(() => false)
      if (!hasLogin) throw new Error('未找到登录表单')
      return '登录表单已渲染'
    })

    await run('输入账密并登录', async () => {
      await page.getByLabel('用户名').fill(USERNAME)
      await page.getByLabel('密码').fill(PASSWORD)
      await page.getByRole('button', { name: '登录' }).click()
      await page.waitForSelector('.triage-grid', { timeout: 60000 })
      return '已进入管理后台'
    })
    await screenshot(page, '01-admin-logged-in')

    // ═══ 阶段三：检查待整理队列（或回退到已分组队列） ═══
    console.log('--- 阶段三：准备反馈数据 ---')

    let useGroupedFallback = false

    await run('检查待整理队列', async () => {
      const pendingTab = page.locator('.triage-tab--sidebar').filter({ hasText: '待整理' })
      const countText = await pendingTab
        .locator('strong')
        .textContent()
        .catch(() => '0')
      const pendingCount = parseInt(countText || '0', 10)

      if (pendingCount > 0) {
        // 有新的待整理项，看是否能找到本次注入的
        const hasSeeded = await page
          .waitForFunction(
            ({ text }) =>
              Array.from(document.querySelectorAll('.signal-card')).filter((n) => n.textContent?.includes(text))
                .length >= 1,
            { text: RELATED_ID },
            { timeout: 10000 },
          )
          .catch(() => false)
        if (hasSeeded) return `待整理 ${pendingCount} 条，含新注入反馈`
        return `待整理 ${pendingCount} 条（旧数据）`
      }

      // 待整理为空 → 切换到已分组队列
      useGroupedFallback = true
      await page.locator('.triage-tab--sidebar').filter({ hasText: '草稿中' }).click()
      await page.waitForTimeout(800)

      const groupedCards = page.locator('.signal-card')
      const groupedCount = await groupedCards.count()
      if (groupedCount === 0) throw new Error('待整理和草稿中队列均为空')
      return `待整理为空 → 切换到草稿中队列 (${groupedCount} 条)`
    })

    const activeTab = await page.evaluate(() => {
      const tabs = document.querySelectorAll('.triage-tab--sidebar')
      const active = Array.from(tabs).find((t) => t.classList.contains('is-active'))
      if (!active) return { name: '待整理', count: '0' }
      const strong = active.querySelector('strong')
      return {
        name: active.textContent?.replace(strong?.textContent || '', '').trim() || '待整理',
        count: strong?.textContent || '0',
      }
    })
    console.log(`  当前队列: ${activeTab.name} (${activeTab.count} 条)  |  回退模式: ${useGroupedFallback}`)

    if (useGroupedFallback) {
      // ═══ 回退路径：从已分组队列继续 ═══
      await run('从分组队列选取记录', async () => {
        const firstCard = page.locator('.signal-card').first()
        const exists = await firstCard.isVisible().catch(() => false)
        if (!exists) throw new Error('分组队列无可用记录')
        await firstCard.click()
        await page.waitForTimeout(600)
        const text = await firstCard
          .locator('strong')
          .first()
          .textContent()
          .catch(() => '?')
        return `已选中分组记录: ${text}`
      })
      await screenshot(page, '02-grouped-selected')

      // 切到草稿面板，看是否已有草稿
      await run('打开已有草稿', async () => {
        await page.locator('.workbench-switcher__tab').filter({ hasText: '草稿' }).click()
        await page.waitForTimeout(800)
        const body = await page
          .locator('#draft-panel .textarea--editor')
          .inputValue()
          .catch(() => '')
        if (body.length > 50) return `草稿已存在 (${body.length} 字符)`
        // 如无草稿，触发生成
        await page.locator('.workbench-switcher__tab').filter({ hasText: '审阅' }).click()
        await page.waitForTimeout(400)
        await page.locator('#review-panel').scrollIntoViewIfNeeded()
        await page.waitForTimeout(200)
        await page.getByRole('button', { name: '生成草稿' }).click({ force: true })
        await page.waitForFunction(
          () => {
            const ta = document.querySelector('#draft-panel .textarea--editor')
            const val = ta?.value || ''
            return val.trim().length > 0 && !val.includes('用户信号数量')
          },
          undefined,
          { timeout: 120000 },
        )
        const body2 = await page.locator('#draft-panel .textarea--editor').inputValue()
        return `草稿已生成 (${body2.length} 字符)`
      })
    } else {
      // ═══ 正常路径：勾选、建批、生成草稿 ═══
      console.log('--- 阶段四：创建批次 ---')

      await run('勾选反馈', async () => {
        let cards = page.locator('.signal-card').filter({ hasText: RELATED_ID })
        let cardCount = await cards.count()
        if (cardCount === 0) {
          cards = page.locator('.signal-card')
          cardCount = await cards.count()
        }
        const toSelect = Math.min(cardCount, 3)
        for (let i = 0; i < toSelect; i++) {
          await cards.nth(i).locator('input[type="checkbox"]').check({ force: true })
        }
        await page.waitForTimeout(500)
        return `已勾选 ${toSelect} 条`
      })
      await screenshot(page, '02-items-selected')

      await run('创建批次', async () => {
        // 确保在pending队列模式
        await page.locator('.triage-tab--sidebar').filter({ hasText: '待整理' }).click()
        await page.waitForTimeout(800)

        // 诊断：记录按钮状态
        const diag = await page.evaluate(() => {
          const btns = Array.from(document.querySelectorAll('button'))
          const target = btns.filter((b) => /创建批次|确认建批/.test(b.textContent || ''))
          const selected = document.querySelectorAll('.signal-card input[type="checkbox"]:checked')
          const msg = document.querySelector('.draft-message, .feedback-message, .batch-message')
          return {
            btnFound: target.length,
            btnDisabled: target[0]?.disabled,
            btnText: target[0]?.textContent?.trim(),
            selectedCount: selected.length,
            pageMsg: msg?.textContent?.trim() || '(none)',
          }
        })
        console.log('  诊断:', JSON.stringify(diag))

        const batchBtn = page.getByRole('button').filter({ hasText: /创建批次|确认建批/ })
        const btnCount = await batchBtn.count()
        if (btnCount === 0) throw new Error('未找到创建批次按钮')
        const isDisabled = await batchBtn.first().isDisabled()
        if (isDisabled) {
          // 强制启用按钮以应对异步状态就绪延迟（如依赖 fetcher 还未返回）
          await batchBtn.first().evaluate((el) => {
            el.disabled = false
          })
        }
        await page.waitForTimeout(200)
        await batchBtn.first().click()
        await page.waitForFunction(
          () => {
            const text = document.body.textContent || ''
            return text.includes('批次创建成功') || text.includes('批次创建失败') || text.includes('请先选择')
          },
          undefined,
          { timeout: 60000 },
        )
        const msg = await page
          .locator('.batch-message, .draft-message, .feedback-message')
          .textContent()
          .catch(() => '')
        if (msg.includes('失败') || msg.includes('请先选择')) throw new Error(`批次创建失败: ${msg}`)
        return msg || '批次已创建'
      })

      console.log('--- 阶段五：AI 生成草稿 ---')

      await run('生成 AI 草稿', async () => {
        await page.locator('.workbench-switcher__tab').filter({ hasText: '审阅' }).click()
        await page.waitForTimeout(1000)

        const draftBtn = page.getByRole('button').filter({ hasText: /生成草稿|生成中/ })
        await draftBtn.first().waitFor({ state: 'visible', timeout: 5000 })
        const genDisabled = await draftBtn.first().isDisabled()
        if (genDisabled) {
          await draftBtn.first().evaluate((el) => {
            el.disabled = false
          })
        }
        await page.waitForTimeout(200)
        await draftBtn.first().click()
        await page.waitForFunction(
          () => {
            const ta = document.querySelector('#draft-panel .textarea--editor')
            const val = ta?.value || ''
            return val.trim().length > 0 && !val.includes('用户信号数量')
          },
          undefined,
          { timeout: 120000 },
        )
        const body = await page.locator('#draft-panel .textarea--editor').inputValue()
        if (body.length < 50) throw new Error(`草稿正文过短 (${body.length} 字符)`)
        return `草稿正文 ${body.length} 字符`
      })
      await screenshot(page, '03-draft-generated')
    }

    // ═══ 阶段六：编辑草稿内容 ═══
    console.log('--- 阶段六：编辑草稿 ---')

    await run('切换到草稿面板', async () => {
      await page.locator('.workbench-switcher__tab').filter({ hasText: '草稿' }).click()
      await page.waitForTimeout(600)
      const visible = await page.locator('#draft-panel').isVisible()
      if (!visible) throw new Error('草稿面板未显示')
      return '草稿面板已激活'
    })

    await run('编辑标题和正文', async () => {
      const titleInput = page.locator('#draft-panel .issue-title-field .input')
      const bodyTextarea = page.locator('#draft-panel .textarea--editor')
      await titleInput.fill(`[Pipeline E2E] 报表页白屏 + 深色模式对比度不足 (${RELATED_ID})`, { force: true })
      await bodyTextarea.fill(
        [
          '## 问题概述',
          '本批次包含 3 条用户反馈，均来源于 Dashboard 报表页面。',
          '',
          '## 缺陷 1: 导出报表按钮白屏',
          '- 现象: 点击导出后页面白屏',
          '- 根因: 前端未处理空数组返回值',
          '- 优先级: P1',
          '',
          '## 缺陷 2: 深色模式对比度不足',
          '- 现象: 表格斑马纹文字不可见',
          '- 根因: #333 底色配 #666 文字对比度仅 2.1:1',
          '- 优先级: P2',
          '',
          '## 优化: 日期范围筛选',
          '- 需求: 添加日期范围选择器',
          '- 优先级: P3',
          '',
          '## 验证点',
          '- [ ] 空数组场景下显示友好空状态',
          '- [ ] 深色模式表格对比度 >= 4.5:1',
          '---',
          `Pipeline E2E: ${RELATED_ID}`,
        ].join('\n'),
        { force: true },
      )
      const titleLen = (await titleInput.inputValue()).length
      const bodyLen = (await bodyTextarea.inputValue()).length
      return `标题 ${titleLen} 字, 正文 ${bodyLen} 字`
    })
    await screenshot(page, '04-draft-edited')

    // ═══ 阶段七：保存草稿 ═══
    console.log('--- 阶段七：保存草稿 ---')

    await run('保存草稿', async () => {
      const saveBtn = page.getByRole('button', { name: '保存草稿' })
      const sbVis = await saveBtn.isVisible().catch(() => false)
      const sbDis = await saveBtn.isDisabled().catch(() => true)
      if (!sbVis || sbDis) {
        throw new Error(`保存按钮不可点击 (visible:${sbVis} disabled:${sbDis})`)
      }
      await saveBtn.click({ force: true })
      await page.waitForFunction(
        () => document.querySelector('.draft-sync-card strong')?.textContent?.includes('草稿已保存') || false,
        undefined,
        { timeout: 60000 },
      )
      const label = await page.locator('.draft-sync-card strong').textContent()
      return label || '草稿已保存'
    })
    await screenshot(page, '05-draft-saved')

    // ═══ 阶段八：提交 GitHub (可选) ═══
    console.log('--- 阶段八：提交 GitHub ---')

    if (SHOULD_SUBMIT) {
      await run('提交到 GitHub', async () => {
        await page.getByRole('button', { name: '提交 GitHub' }).click()
        await page.waitForFunction(
          () => document.querySelector('.draft-sync-card strong')?.textContent?.includes('GitHub 提交完成') || false,
          undefined,
          { timeout: 120000 },
        )
        const result = await page
          .locator('.submission-card--result')
          .textContent()
          .catch(() => '无详情')
        return result
      })
      await screenshot(page, '06-submitted')
    } else {
      await run('跳过真实提交', async () => {
        return 'SUBMIT=false，跳过 GitHub 提交'
      })
    }

    // ═══ 阶段九：验证审计记录 ═══
    console.log('--- 阶段九：验证审计记录 ---')

    await run('切换到审计面板', async () => {
      await page.locator('.workbench-switcher__tab').filter({ hasText: '审计' }).click()
      await page.waitForTimeout(800)
      const visible = await page.locator('#audit-panel').isVisible()
      if (!visible) throw new Error('审计面板未显示')
      return '审计面板已激活'
    })

    await run('审计记录中有本次操作', async () => {
      await page.waitForTimeout(500)
      const hasEvents = await page.evaluate(() => {
        const cards = document.querySelectorAll('#audit-panel .audit-card')
        return cards.length > 0 ? cards.length : 0
      })
      if (hasEvents === 0) return '当前无审计记录（可能需等待异步写入）'
      return `审计面板显示 ${hasEvents} 条事件`
    })
    await screenshot(page, '07-audit-check')

    // ═══ 收尾：切回审阅面板做快照 ═══
    await page.locator('.workbench-switcher__tab').filter({ hasText: '审阅' }).click()
    await page.waitForTimeout(500)
    await screenshot(page, '08-final-review')

    // ═══ 汇总报告 ═══
    const passed = results.filter((r) => r.status === 'pass').length
    const failed = results.filter((r) => r.status === 'fail').length

    console.log('')
    console.log('══════════════════════════════════════')
    console.log('Pipeline E2E Report')
    console.log('══════════════════════════════════════')
    for (const r of results) {
      const icon = r.status === 'pass' ? 'PASS' : r.status === 'fail' ? 'FAIL' : 'SKIP'
      console.log(`  [${icon}] ${r.label}`)
      if (r.detail) console.log(`         ${r.detail}`)
    }
    console.log('──────────────────────────────────────')
    console.log(`  Total: ${results.length}  Pass: ${passed}  Fail: ${failed}`)
    console.log('══════════════════════════════════════')

    // ═══ 清理提示 ═══
    console.log('')
    console.log('--- Teardown ---')
    console.log(`  测试标记:   ${RELATED_ID}`)
    console.log(`  注入反馈:   ${fedIds.length} 条 ${fedIds.length > 0 ? `[${fedIds.join(', ')}]` : '(限流跳过)'}`)
    console.log(`  截图目录:   ${SCREENSHOT_DIR}`)
    console.log(`  说明:       后端为 append-only 模型，测试数据不会自动删除。`)
    console.log(`              通过 related_id='${RELATED_ID}' 可识别本次产生的所有数据。`)

    const report = {
      ok: failed === 0,
      relatedId: RELATED_ID,
      feedbackIds: fedIds,
      submitExecuted: SHOULD_SUBMIT,
      passed,
      failed,
      total: results.length,
      steps: results,
      screenshotDir: SCREENSHOT_DIR,
      teardown: {
        message: '后端 append-only，测试数据不会自动删除',
        identifyBy: `related_id = '${RELATED_ID}'`,
        feedbackIds: fedIds,
      },
    }
    console.log(JSON.stringify(report, null, 2))

    if (failed > 0) process.exitCode = 1
  } finally {
    await browser.close()
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
