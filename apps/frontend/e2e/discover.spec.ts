import { expect, test } from '@playwright/test'

test.use({ javaScriptEnabled: false })

const API = 'http://localhost:8000'

type LotRow = { public_slug?: string }

async function liveDiscoverSlug(): Promise<{ apiDown: boolean; slug: string | null }> {
  const health = await fetch(`${API}/health`).catch(() => null)
  if (!health?.ok) return { apiDown: true, slug: null }

  const listed = await fetch(`${API}/api/v1/lots`).catch(() => null)
  if (!listed?.ok) return { apiDown: false, slug: null }
  const lots = (await listed.json()) as LotRow[]
  if (!Array.isArray(lots)) return { apiDown: false, slug: null }

  for (const lot of lots) {
    if (!lot.public_slug) continue
    const snap = await fetch(`${API}/api/v1/discover/${encodeURIComponent(lot.public_slug)}`).catch(
      () => null
    )
    if (snap?.ok) return { apiDown: false, slug: lot.public_slug }
  }
  return { apiDown: false, slug: null }
}

test('discover renders without JavaScript and leaks no commercial fields', async ({ page }) => {
  const found = await liveDiscoverSlug()
  test.skip(found.apiDown, 'live API is not running')
  test.skip(!found.slug, 'no live lot with a public snapshot')

  await page.goto(`/discover/${found.slug}`)
  await expect(page.locator('body')).toContainText(/Fishora|cara memasak/i)
  const text = await page.locator('body').innerText()
  expect(text).not.toMatch(/Rp|penawaran|Dewi Anggraini|\bbuyer\b|volume|68\.000/i)
})
