import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Invariants that hold on every surface, checked on every surface. `/` is the
// marketing landing, not the foundations kit: the kit moved to /kit, so aiming
// these at `/` alone both missed the app and asserted the wrong page.
const ROUTES = ['/', '/kit', '/operator', '/marketplace', '/preferences', '/account'] as const

// A settled theme, not a mid-transition frame: contrast measured during a fade
// is neither the light value nor the dark one.
const FREEZE = '*, *::before, *::after { transition: none !important; animation: none !important; }'

for (const route of ROUTES) {
  test(`${route} never scrolls horizontally`, async ({ page }) => {
    await page.goto(route)
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    )
    expect(overflow, `${route} overflows by ${overflow}px`).toBeLessThanOrEqual(0)
  })

  test(`${route} has no axe violations`, async ({ page }) => {
    await page.goto(route)
    await page.addStyleTag({ content: FREEZE })
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze()
    expect(
      results.violations,
      `${route}: ${JSON.stringify(results.violations, null, 2)}`
    ).toEqual([])
  })

  test(`${route} keeps interactive targets at 44px`, async ({ page }, testInfo) => {
    test.skip(!testInfo.project.name.startsWith('phone'), 'target size is a touch constraint')
    await page.goto(route)
    // Scoped to the document rather than a Playwright locator, which pierces
    // shadow DOM and would flag the Next dev-tools badge as our UI.
    const undersized = await page.evaluate(() => {
      const out: string[] = []
      for (const el of document.querySelectorAll<HTMLElement>('button, a[href], input, select')) {
        const style = getComputedStyle(el)
        if (style.display === 'none' || style.visibility === 'hidden') continue
        // A checkbox or file input is tapped through its label, so the label is
        // the real target. Measuring the control alone reports a false failure.
        const target = el.closest('label') ?? el
        const box = target.getBoundingClientRect()
        // Zero-size or 1px controls are visually hidden triggers, not targets.
        if (box.width < 2 || box.height < 2) continue
        if (box.height < 44 || box.width < 44) {
          const text = (target.textContent ?? '').trim().slice(0, 30) || `<${el.tagName.toLowerCase()}>`
          out.push(`${text} ${Math.round(box.width)}x${Math.round(box.height)}`)
        }
      }
      return out
    })
    expect(undersized, `${route} undersized: ${undersized.join(' | ')}`).toEqual([])
  })
}

test('the app surfaces honour an explicit theme choice in both directions', async ({ page }) => {
  await page.goto('/kit')
  await page.addStyleTag({ content: FREEZE })

  const groundFor = async (theme: string) => {
    await page.evaluate((value) => {
      document.documentElement.setAttribute('data-theme', value)
    }, theme)
    return page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  }

  const light = await groundFor('light')
  const dark = await groundFor('dark')
  expect(light).not.toBe(dark)
  // Neither ground may be pure black or pure white. DESIGN.md 8.B.
  expect(dark).not.toBe('rgb(0, 0, 0)')
  expect(light).not.toBe('rgb(255, 255, 255)')
})
