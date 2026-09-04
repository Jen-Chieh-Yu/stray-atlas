import { copyFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

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

export default defineConfig({
  // GitHub Pages serves this as a project site under /stray-atlas/.
  // CLAUDE.md 2.2: this, the router base, and every data fetch have to agree,
  // or `npm run dev` looks fine and the deployed page is blank with 404s.
  base: '/stray-atlas/',
  plugins: [vue(), pagesSpaFallback()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
