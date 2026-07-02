import { defineConfig } from '@playwright/test'
import baseConfig from './playwright.config'

// One-off config for recording a demo video of the registrator e2e flow.
// Not used in CI — see playwright.config.ts for the real test configuration.
export default defineConfig({
  ...baseConfig,
  use: {
    ...baseConfig.use,
    video: 'on'
  }
})
