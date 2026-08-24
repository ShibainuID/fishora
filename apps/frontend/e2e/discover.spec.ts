import { expect, test } from '@playwright/test'

test.use({ javaScriptEnabled: false })

test('discover renders without JavaScript and leaks no commercial fields', async ({ page }) => {
  test.skip(true, 'requires a live API snapshot; enabled in the MVP walkthrough when the backend is up')
  await page.goto('/discover/tenggiri-lot1')
  const text = await page.locator('body').innerText()
  expect(text).not.toMatch(/Rp|penawaran|buyer|volume|68.000/i)
})
