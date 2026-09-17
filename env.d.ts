/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

interface ImportMetaEnv {
  /** Google Maps Embed API key for the shelter page map. Optional: without
   *  it the page links out to Google Maps instead of embedding. Set it in
   *  .env.local for development and as a repository secret for the deploy. */
  readonly VITE_GOOGLE_MAPS_EMBED_KEY?: string
}
