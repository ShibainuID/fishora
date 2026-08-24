import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('page body never scrolls horizontally', async ({ page }) => {
  await page.goto('/')
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  expect(overflow).toBeLessThanOrEqual(0)
})

test('every interactive target clears 44px', async ({ page }) => {
  await page.goto('/')
  const targets = page.locator('button:visible, a:visible, input:visible')
  const undersized: string[] = []
  for (let i = 0; i < (await targets.count()); i++) {
    const el = targets.nth(i)
    const box = await el.boundingBox()
    if (box && (box.height < 44 || box.width < 44)) {
      undersized.push(`${await el.innerText()} ${box.width}x${box.height}`)
    }
  }
  expect(undersized, `undersized targets: ${undersized.join(', ')}`).toEqual([])
})

test('no axe violations in either theme', async ({ page }) => {
  await page.goto('/')
  // Audit the settled theme, not a mid-fade interpolation.
  await page.addStyleTag({
    content: '*, *::before, *::after { transition: none !important; animation: none !important; }',
  })
  for (const theme of ['light', 'dark']) {
    await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme)
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze()
    expect(results.violations, `${theme}: ${JSON.stringify(results.violations, null, 2)}`).toEqual([])
  }
})
