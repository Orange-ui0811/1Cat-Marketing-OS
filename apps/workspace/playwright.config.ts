import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  reporter: [['list'], ['html', { outputFolder: '../../.runtime/playwright-report', open: 'never' }]],
  use: {
    baseURL: process.env.ONECAT_BASE_URL || 'http://localhost:8080',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
