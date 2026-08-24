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
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
  ],
})
