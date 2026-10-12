import { defineConfig, devices } from '@playwright/test'

/** Smoke tests against the production build, served under the same
 *  /stray-atlas/ sub-path as GitHub Pages.
 *
 *  They exist for one class of bug: the page that works on `npm run dev` and
 *  is blank once deployed (CLAUDE.md 2.2). Unit tests cannot see it, because
 *  it lives in the base path, the router and the fetch URLs agreeing with
 *  each other. Run `npm run build` first; this serves dist/ as it stands.
 */
const PORT = 4173

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: `http://localhost:${PORT}/stray-atlas/`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npx vite preview --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}/stray-atlas/`,
    reuseExistingServer: !process.env.CI,
  },
})
