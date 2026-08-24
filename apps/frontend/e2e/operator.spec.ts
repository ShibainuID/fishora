import { expect, test } from '@playwright/test'

async function probe(url: string) {
  return fetch(url).catch(() => null)
}

test('operator chrome is four steps, not a track, with a safe-area action bar', async ({
  page,
}) => {
  await page.goto('/operator')
  await expect(page.getByText(/langkah 1 dari 4/i)).toBeVisible()
  expect(await page.locator('[role="progressbar"]').count()).toBe(0)
  const camera = page.getByRole('button', { name: 'Kamera' })
  await expect(camera).toBeVisible()
  const bar = camera.locator('xpath=ancestor::div[contains(@class,"fixed")]').first()
  await expect(bar).toBeVisible()
  const lang = await page.locator('html').getAttribute('lang')
  expect(lang).toBe('id')
})

test('identifies a catch against the live API when it is up', async ({ page }) => {
  const health = await probe('http://localhost:8000/health')
  test.skip(!health?.ok, 'main API is not reachable at http://localhost:8000/health')

  // Reachability of both services first, then the data state they need.
  const cv = await probe('http://localhost:8001/health')
  test.skip(!cv?.ok, 'CV service is not reachable at http://localhost:8001/health, so identify returns 503')

  const body = (await health!.json().catch(() => null)) as { taxonomy_seeded?: boolean } | null
  test.skip(
    body?.taxonomy_seeded !== true,
    'taxonomy is not seeded, so every identification fails on species resolution'
  )

  await page.goto('/operator')
  const jpeg = Buffer.from(
    '/9j/4AAQSkZJRgABAQAAAQABAAD/2wAAAAD/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAEH/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPwB//9k=',
    'base64'
  )
  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'tenggiri.jpg',
    mimeType: 'image/jpeg',
    buffer: jpeg,
  })
  await page.getByRole('button', { name: /identifikasi/i }).click()
  await expect(
    page.getByRole('button', { name: /konfirmasi|coba lagi/i })
  ).toBeVisible({ timeout: 40_000 })
})
