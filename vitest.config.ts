import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

/** Test config, separate from vite.config.ts on purpose.
 *
 *  vite.config.ts carries the GitHub Pages base path and the 404.html writer
 *  (CLAUDE.md 2.2); none of that belongs in a test run, and mixing them is
 *  how a build setting ends up depending on a test setting. The alias is the
 *  one thing both need, so it is repeated rather than shared — four lines
 *  against an import cycle between the two configs.
 *
 *  Environment is node: these tests cover pure functions in src/lib. The day
 *  a component test arrives, it declares `// @vitest-environment jsdom` at
 *  the top of its own file rather than slowing every other test down.
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.spec.ts'],
  },
})
