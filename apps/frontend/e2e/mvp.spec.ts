import { expect, test, type Page } from '@playwright/test'

const API = 'http://localhost:8000'
const JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQAAAQABAAD/2wAAAAD/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAEH/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPwB//9k=',
  'base64'
)

async function signIn(page: Page, username: string, password: string) {
  await page.goto('/account')
  const keluar = page.getByRole('button', { name: 'Keluar' })
  if (await keluar.isVisible()) {
    await keluar.click()
  }
  await page.getByLabel('Nama pengguna').fill(username)
  await page.getByLabel('Kata sandi').fill(password)
  await page.getByRole('button', { name: 'Masuk' }).click()
  await expect(page.getByRole('button', { name: 'Keluar' })).toBeVisible({ timeout: 15_000 })
}

function assertNoCommercialLeak(text: string) {
  expect(text).not.toMatch(/Rp|penawaran|Dewi Anggraini|\bbuyer\b|volume|68\.000/i)
}

test('PRD 27 eleven-step walkthrough against a live backend when it is up', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'PRD walkthrough runs on the phone project')
  test.setTimeout(180_000)

  const health = await fetch(`${API}/health`).catch(() => null)
  test.skip(!health?.ok, 'live API is not running')
  // An unseeded taxonomy answers 200 but fails every species resolution, so
  // skip with the real reason instead of failing deep inside step 3.
  const ready = (await health!.json()) as { taxonomy_seeded?: boolean }
  test.skip(
    !ready.taxonomy_seeded,
    'taxonomy is not seeded: run scripts.seed_taxonomy (needs the dataset artifact)'
  )

  await test.step('1. Operator login at /account', async () => {
    await signIn(page, 'rian', 'demo')
    await expect(page.getByText('Rian Setiawan')).toBeVisible()
  })

  await test.step('2. Identify at /operator', async () => {
    await page.goto('/operator')
    await expect(page.getByText(/langkah 1 dari 4/i)).toBeVisible()
    await page.locator('input[type="file"]').first().setInputFiles({
      name: 'tenggiri.jpg',
      mimeType: 'image/jpeg',
      buffer: JPEG,
    })
    await page.getByRole('button', { name: /identifikasi/i }).click()
    const confirm = page.getByRole('button', { name: 'Konfirmasi' })
    const retry = page.getByRole('button', { name: /coba lagi/i })
    await expect(confirm.or(retry)).toBeVisible({ timeout: 40_000 })
  })

  const identified = await page.getByRole('button', { name: 'Konfirmasi' }).isVisible()

  await test.step('3. Verify the species, by model or by hand', async () => {
    if (identified) {
      await page.getByRole('button', { name: 'Konfirmasi' }).click()
      return
    }
    // CV is down. The operator names the species instead, which still produces
    // a verified prediction, so publication is not blocked.
    test.info().annotations.push({
      type: 'note',
      description: 'CV unavailable: species declared manually (PRD 8.1 human-in-the-loop path)',
    })
    await page.getByRole('button', { name: /pilih spesies manual/i }).click()
    await page.getByRole('button', { name: 'tenggiri', exact: true }).click()
  })

  await test.step('4. Knowledge / Lanjut', async () => {
    await expect(page.getByRole('button', { name: 'Lanjut' })).toBeVisible({ timeout: 60_000 })
    await expect(page.getByText(/langkah 3 dari 4/i)).toBeVisible()
    await page.getByRole('button', { name: 'Lanjut' }).click()
  })

  await test.step('5. Publish Terbitkan', async () => {
    await expect(page.getByText(/langkah 4 dari 4/i)).toBeVisible()
    await page.getByLabel(/Kuantitas/).fill('24')
    await page.getByLabel(/Harga awal/).fill('68000')
    await page.getByRole('button', { name: 'Terbitkan' }).click()
    await expect(page.getByRole('heading', { name: /lot saya/i })).toBeVisible({ timeout: 30_000 })
  })

  await test.step('6. Buyer login dewi / demo', async () => {
    await signIn(page, 'dewi', 'demo')
    await expect(page.getByText('Dewi Anggraini')).toBeVisible()
  })

  await test.step('7. Marketplace browse', async () => {
    await page.goto('/marketplace')
    await expect(page.getByRole('button', { name: /filters/i })).toBeVisible()
    await page.locator('a[href^="/marketplace/"]').first().click()
  })

  await test.step('8. Place a bid on the lot', async () => {
    await page.getByRole('button', { name: 'Ajukan penawaran' }).click()
    await page.getByLabel(/Harga per kg/).fill('69000')
    await page.getByRole('button', { name: 'Kirim' }).click()
    await expect(page.getByRole('button', { name: 'Ajukan penawaran' })).toBeVisible({
      timeout: 15_000,
    })
  })

  await test.step('9. Operator Tutup lelang then Allocate', async () => {
    await signIn(page, 'rian', 'demo')
    await page.goto('/operator/lots')
    const lotRow = page.locator('main ul > li').first()
    await lotRow.getByRole('button', { name: 'Tutup lelang' }).click()
    await page.getByRole('button', { name: 'Konfirmasi tutup' }).click()
    await expect(lotRow.getByRole('button', { name: 'Allocate to winning bidder' })).toBeVisible()
    await lotRow.getByRole('button', { name: 'Allocate to winning bidder' }).click()
    await page.getByRole('button', { name: 'Konfirmasi' }).click()
  })

  const discoverPath = await test.step('10. Buat QR / copy discover URL', async () => {
    const copy = page.getByRole('button', { name: 'Salin URL' })
    if (!(await copy.isVisible())) {
      await page.getByRole('button', { name: 'Buat QR' }).first().click()
    }
    await expect(copy).toBeVisible()
    const href = await page.getByLabel('URL').inputValue()
    expect(href).toMatch(/\/discover\//)
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    await copy.click()
    await expect(page.getByRole('button', { name: /Salin URL|Disalin/ })).toBeVisible()
    return new URL(href).pathname
  })

  await test.step('11. Public Discover page has no commercial leak', async () => {
    await page.goto(discoverPath)
    await expect(page.locator('body')).toContainText(/Fishora|cara memasak/i)
    assertNoCommercialLeak(await page.locator('body').innerText())
  })
})
