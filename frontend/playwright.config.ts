import { defineConfig, devices } from '@playwright/test'

// Bundled Chromium build doesn't match this @playwright/test version in the
// sandbox image; point at the pre-installed browser explicitly instead of
// trying to download one (see /root/.ccr/README.md in this environment).
const chromiumExecutable =
  process.env.PLAYWRIGHT_CHROMIUM_PATH ||
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

export default defineConfig({
  testDir: './tests/e2e',
  // Outbound requests to a handful of external CDNs (icon/font hosts) are
  // blocked by this sandbox's network policy and only fail after a slow
  // timeout, so the very first hard page load of a test can take 10s+ on its
  // own. A generous test timeout absorbs that without masking real bugs.
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  // The sandboxed Chromium build is a version behind this @playwright/test
  // release and occasionally drops the CDP connection under load (flaky
  // browser-process crash, unrelated to app behavior) — retry absorbs it.
  retries: 2,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5177',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: {
      executablePath: chromiumExecutable,
      args: ['--no-sandbox']
    }
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
})
