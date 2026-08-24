import { expect, test } from '@playwright/test'

// The mechanically checkable half of the DESIGN.md section 15 pre-flight. Kept
// as tests rather than a checklist so it cannot quietly rot: three palette bugs
// already survived a visual review.

test('zero em or en dashes anywhere in visible copy', async ({ page }) => {
  for (const route of ['/', '/kit', '/operator', '/marketplace', '/preferences', '/account']) {
    await page.goto(route)
    const text = await page.locator('body').innerText()
    const offenders = text.match(/.{0,30}[—–].{0,30}/g)
    expect(offenders, `${route}: ${offenders?.join(' | ')}`).toBeNull()
  }
})

test('landing keeps the eyebrow budget and one label per CTA intent', async ({ page }) => {
  await page.goto('/')
  const sections = await page.locator('section').count()
  const eyebrows = await page.locator('.text-eyebrow').count()
  // At most one eyebrow per three sections. DESIGN.md 4.7.
  expect(eyebrows, `${eyebrows} eyebrows across ${sections} sections`).toBeLessThanOrEqual(
    Math.ceil(sections / 3)
  )

  const labels = await page.locator('a, button').allTextContents()
  const trimmed = labels.map((row) => row.trim())
  // Exactly two CTA intents, one label each: no "Get in touch" plus "Let's talk".
  const contact = trimmed.filter((row) => /request access|get started|sign up|contact/i.test(row))
  expect(new Set(contact).size).toBeLessThanOrEqual(1)
  const tour = trimmed.filter((row) => /see the flow|learn more|how it works/i.test(row))
  expect(new Set(tour).size).toBeLessThanOrEqual(1)
})

test('landing hero fits the first viewport with both CTAs reachable', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'the hero budget is a phone constraint')
  await page.goto('/')
  const viewport = page.viewportSize()!

  const primary = page.getByRole('link', { name: 'Request access' }).first()
  const secondary = page.getByRole('link', { name: 'See the flow' }).first()
  for (const cta of [primary, secondary]) {
    const box = await cta.boundingBox()
    expect(box, 'hero CTA is not rendered').not.toBeNull()
    // Visible without scrolling: a CTA below the fold is not in the hero.
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height)
  }
})

test('landing is readable with JavaScript disabled', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false })
  const page = await context.newPage()
  await page.goto('/')
  await expect(page.getByText(/Discover the value beneath the ocean/i).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'Request access' }).first()).toBeVisible()
  await context.close()
})

test('the landing page is theme-locked and does not follow an override', async ({ page }) => {
  await page.goto('/')
  const ground = async (theme: string) => {
    await page.evaluate((value) => {
      document.documentElement.setAttribute('data-theme', value)
    }, theme)
    return page.evaluate(() =>
      getComputedStyle(document.querySelector('[data-block], main, body')!).backgroundColor
    )
  }
  // DESIGN.md 5: the landing is dark by brand, so a light override must not
  // flip it mid-page.
  expect(await ground('light')).toBe(await ground('dark'))
})

test('no fixed element ignores the safe area on phones', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'safe-area padding is a phone constraint')
  for (const route of ['/operator', '/preferences']) {
    await page.goto(route)
    const offenders = await page.evaluate(() =>
      [...document.querySelectorAll('*')]
        .filter((el) => {
          const style = getComputedStyle(el)
          if (style.position !== 'fixed') return false
          const rect = el.getBoundingClientRect()
          const atBottom = Math.abs(rect.bottom - window.innerHeight) < 2
          return atBottom && !style.paddingBottom.includes('px')
        })
        .map((el) => el.className)
    )
    expect(offenders, `${route}: ${offenders.join(' | ')}`).toEqual([])
  }
})

test('a sheet is hidden when closed and actually paints when open', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'phone', 'the filter sheet is the phone affordance')
  await page.goto('/marketplace')

  const sheet = page.getByRole('dialog', { name: /filter/i })
  // Closed: a bare `flex` on the dialog would override the browser rule that
  // keeps a closed dialog hidden, leaving the panel over the whole page.
  await expect(sheet).toBeHidden()

  await page.getByRole('button', { name: /filter/i }).first().click()

  // Open: the fix for the above must not overshoot into a `hidden` that wins the
  // cascade, which would render the sheet permanently unreachable instead.
  await expect(sheet).toBeVisible()
  const box = await sheet.boundingBox()
  expect(box?.height ?? 0).toBeGreaterThan(0)
})
