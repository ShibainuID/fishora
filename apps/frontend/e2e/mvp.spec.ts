import { expect, test } from '@playwright/test'

test('PRD 27 walkthrough against a live backend when it is up', async ({ page }) => {
  const health = await fetch('http://localhost:8000/health').catch(() => null)
  test.skip(!health?.ok, 'live API is not running')

  await page.goto('/operator')
  await expect(page.getByText(/langkah 1 dari 4/i)).toBeVisible()
  await page.goto('/marketplace')
  await expect(page.getByRole('button', { name: /filters/i })).toBeVisible()
  await page.goto('/preferences')
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
  await page.goto('/operator/lots')
  await expect(page.getByRole('heading', { name: /lot saya/i })).toBeVisible()
  await page.goto('/')
  await expect(page.getByText(/Discover the value beneath the ocean/i).first()).toBeVisible()
})
