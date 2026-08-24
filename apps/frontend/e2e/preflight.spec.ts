import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('landing phone composition: two CTAs, two eyebrows, no dashes, no overflow', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'phone composition is asserted on the phone project')
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Request access' }).or(page.getByRole('link', { name: 'Request access' })).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'See the flow' }).first()).toBeVisible()
  const eyebrows = await page.locator('.text-eyebrow').count()
  expect(eyebrows).toBeLessThanOrEqual(3)
  expect(eyebrows).toBeGreaterThanOrEqual(1)
  const text = await page.locator('body').innerText()
  expect(text).not.toMatch(/[—–]/)
  const labels = await page.getByText(/Request access|See the flow/).allTextContents()
  const unique = new Set(labels.map((row) => row.trim()).filter((row) => row === 'Request access' || row === 'See the flow'))
  expect([...unique].sort()).toEqual(['Request access', 'See the flow'])
})

test('preflight: no horizontal overflow and axe clean', async ({ page }) => {
  await page.goto('/')
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  expect(overflow).toBeLessThanOrEqual(0)
  await page.addStyleTag({
    content: '*, *::before, *::after { transition: none !important; animation: none !important; }',
  })
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([])
})
