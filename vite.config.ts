import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { daysInShelter } from './src/lib/days'
import { sharePageHtml } from './src/lib/share'
import type { Animal, ShelterPayload } from './src/types'

// GitHub Pages serves this as a project site under /stray-atlas/.
// CLAUDE.md 2.2: this, the router base, and every data fetch have to agree,
// or `npm run dev` looks fine and the deployed page is blank with 404s.
const BASE = '/stray-atlas/'

/** GitHub Pages has no server-side rewrite, so a refresh on /shelters/<id>
 *  hits its 404 page. Serving the app from 404.html is the standard fix; it
 *  has to be a copy of the built index.html, not of the source, because of the
 *  hashed asset names. */
function pagesSpaFallback() {
  return {
    name: 'pages-spa-fallback',
    closeBundle() {
      copyFileSync('dist/index.html', 'dist/404.html')
    },
  }
}

/** One small page per animal at /a/<id>/, so a shared link previews that
 *  animal; src/lib/share.ts has the why. Built from the same public/data the
 *  site ships, so each deploy's pages match its roster: the daily rebuild
 *  redeploys, and an animal that left the list loses its page. */
function sharePages() {
  return {
    name: 'share-pages',
    apply: 'build' as const,
    closeBundle() {
      const animals = JSON.parse(readFileSync('public/data/animals.json', 'utf-8')) as Animal[]
      const shelters = JSON.parse(
        readFileSync('public/data/shelters.json', 'utf-8'),
      ) as ShelterPayload
      const nameOf = new Map(shelters.shelters.map((shelter) => [shelter.id, shelter.name]))
      const snapshot = shelters.snapshot_date
      for (const animal of animals) {
        // A path segment. The source's ids are all digits; anything else is
        // skipped rather than written somewhere unexpected.
        if (!/^\d+$/.test(animal.id)) continue
        const dir = `dist/a/${animal.id}`
        mkdirSync(dir, { recursive: true })
        writeFileSync(
          `${dir}/index.html`,
          sharePageHtml(
            animal,
            nameOf.get(animal.shelter) ?? '',
            daysInShelter(animal.created, snapshot),
            snapshot,
            BASE,
          ),
        )
      }
    },
  }
}

export default defineConfig({
  base: BASE,
  plugins: [vue(), pagesSpaFallback(), sharePages()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
