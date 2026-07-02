import { test as base, expect } from '@playwright/test'

/**
 * `index.html` loads a dev-only feedback/annotation widget
 * (`/feedback/annotator.min.js`) on every page. Its "annotation mode" can
 * freeze all UI interaction ("UI заморожен, клик отмечает элемент"), which
 * has nothing to do with the registrator flow but breaks automated clicks.
 * Block it for the whole suite instead of touching app markup.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route('**/feedback/annotator.min.js', (route) => route.abort())
    await use(page)
  }
})

export { expect }
