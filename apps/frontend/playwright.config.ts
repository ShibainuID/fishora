import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: 'list',
  use: { baseURL: 'http://localhost:3111', trace: 'on-first-retry' },
  webServer: {
    command: 'pnpm dev --port 3111',
    url: 'http://localhost:3111',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    // Phone first, and named so a failure says which viewport broke.
    { name: 'phone', use: { ...devices['Pixel 7'] } },
    // 390px is the narrowest width DESIGN.md commits to, and Pixel 7 is 412.
    // Without this the narrowest layout is only ever eyeballed.
    {
      name: 'phone-390',
      use: {
        ...devices['iPhone 13 mini'],
        viewport: { width: 390, height: 844 },
      },
    },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
  ],
})
