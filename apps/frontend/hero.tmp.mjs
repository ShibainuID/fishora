import { chromium } from '@playwright/test'
const out = process.argv[2]
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
const p = await ctx.newPage()
await p.goto('http://localhost:3111/', { waitUntil: 'networkidle' })
await p.waitForTimeout(1000)
// The track is 240vh; sample the descent at four depths.
for (const [i, y] of [0, 500, 1100, 1700].entries()) {
  await p.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), y)
  await p.waitForTimeout(600)
  await p.screenshot({ path: `${out}/hero-${i}-${y}.png` })
}
await b.close()
