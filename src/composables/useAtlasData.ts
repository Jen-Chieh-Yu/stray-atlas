import { ref } from 'vue'
import type { Animal, CountyCollection, CountyPayload, ShelterPayload } from '@/types'

/** Data lives in public/ and is served from the Pages sub-path.
 *
 * CLAUDE.md 2.2: this must go through BASE_URL. An absolute '/data/...' works
 * on `npm run dev` and 404s on GitHub Pages, which is the trap that makes the
 * deployed page blank while everything looks fine locally.
 */
function dataUrl(name: string): string {
  return `${import.meta.env.BASE_URL}data/${name}`
}

/** Flip every ring so d3-geo reads the polygons as land rather than ocean.
 *
 * The files on disk follow RFC 7946: exterior rings counter-clockwise, holes
 * clockwise. d3-geo predates that RFC and uses the opposite spherical
 * convention — a counter-clockwise exterior ring is a polygon covering
 * everything OUTSIDE it, which renders as a rectangle filling the viewport.
 * Reversing both ring kinds converts one convention to the other exactly.
 *
 * Done here rather than in the published file so data/ stays valid GeoJSON
 * for anything else that reads it. It is one pass over ~23k coordinates.
 */
function rewindForD3(collection: CountyCollection): CountyCollection {
  for (const feature of collection.features) {
    for (const polygon of feature.geometry.coordinates) {
      for (const ring of polygon) ring.reverse()
    }
  }
  return collection
}

// Module scope, not per-call: the masthead and the map both want the snapshot
// date, and the county file should be fetched once per visit rather than once
// per component.
const stats = ref<CountyPayload | null>(null)
const shapes = ref<CountyCollection | null>(null)
const error = ref<string | null>(null)
const loading = ref(true)
let started = false

export function useAtlasData() {

  async function load() {
    loading.value = true
    error.value = null
    try {
      const [statsResponse, shapesResponse] = await Promise.all([
        fetch(dataUrl('stats/counties.json')),
        fetch(dataUrl('counties.geojson')),
      ])
      if (!statsResponse.ok || !shapesResponse.ok) {
        throw new Error(`${statsResponse.status} / ${shapesResponse.status}`)
      }
      stats.value = (await statsResponse.json()) as CountyPayload
      shapes.value = rewindForD3((await shapesResponse.json()) as CountyCollection)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : String(cause)
    } finally {
      loading.value = false
    }
  }

  if (!started) {
    started = true
    void load()
  }
  return { stats, shapes, loading, error, reload: load }
}

let sheltersOnce: Promise<ShelterPayload> | null = null
let animalsOnce: Promise<Animal[]> | null = null

/** Both files are fetched at most once per visit and shared by every view.
 *  animals.json is 272 KB gzipped for all 8,265 records — more than a single
 *  shelter needs, but it is fetched once and then serves the shelter page and
 *  the browse-everything page alike, with no second copy to drift. */
export function fetchShelters(): Promise<ShelterPayload> {
  sheltersOnce ??= fetch(dataUrl('shelters.json')).then((response) => {
    if (!response.ok) throw new Error(`shelters.json ${response.status}`)
    return response.json() as Promise<ShelterPayload>
  })
  return sheltersOnce
}

export function fetchAnimals(): Promise<Animal[]> {
  animalsOnce ??= fetch(dataUrl('animals.json')).then((response) => {
    if (!response.ok) throw new Error(`animals.json ${response.status}`)
    return response.json() as Promise<Animal[]>
  })
  return animalsOnce
}

/** Days in the shelter, measured against the snapshot rather than today. */
export function daysInShelter(created: string, snapshotDate: string): number | null {
  const from = Date.parse(created)
  const to = Date.parse(snapshotDate)
  if (Number.isNaN(from) || Number.isNaN(to)) return null
  return Math.round((to - from) / 86400000)
}
