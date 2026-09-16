import type { LocationQuery } from 'vue-router'
import type { Kind } from '@/types'

/* Animal helpers shared across pages.
 *
 *  Used by: HomeView.vue and AnimalsView.vue (labels, day bands, the /animals
 *  query contract, counting helpers) and AnimalCard.vue (SEX_LABEL,
 *  formatCount).
 */

/** Display labels for the coded columns. One copy, shared by every page. */
export const SEX_LABEL: Record<string, string> = { M: '公', F: '母', N: '未填' }
export const BODY_LABEL: Record<string, string> = { SMALL: '小型', MEDIUM: '中型', BIG: '大型' }
export const AGE_LABEL: Record<string, string> = { CHILD: '幼體', ADULT: '成體' }

/** 已在所 bands, as the find-animals draft lists them. The key is what goes in
 *  the URL, so a link from the home page survives a relabel. */
export const DAY_BANDS = [
  { key: '0-30', label: '30 天內', min: 0, max: 30 },
  { key: '31-90', label: '31–90 天', min: 31, max: 90 },
  { key: '91-365', label: '91–365 天', min: 91, max: 365 },
  { key: '1-2y', label: '1–2 年', min: 366, max: 730 },
  { key: '2-5y', label: '2–5 年', min: 731, max: 1825 },
  { key: '5y+', label: '5 年以上', min: 1826, max: null },
] as const

export type DayBandKey = (typeof DAY_BANDS)[number]['key']

export function inBand(days: number | null, min: number, max: number | null): boolean {
  return days !== null && days >= min && (max === null || days <= max)
}

/** URL form of 狗／貓／其他. */
export const KIND_PARAM: Record<Kind, string> = { 狗: 'dog', 貓: 'cat', 其他: 'other' }
const KIND_FROM_PARAM: Record<string, Kind> = { dog: '狗', cat: '貓', other: '其他' }

export const SORTS = [
  { id: 'longest', label: '已在所天數（長到短）' },
  { id: 'shortest', label: '已在所天數（短到長）' },
] as const

/** The query contract of /animals. The home page builds links against it now;
 *  the find-animals page reads it when that page is rebuilt. Every key is
 *  optional and an absent key means "no filter". */
export interface AnimalQuery {
  kind?: Kind
  county?: string
  shelter?: string
  variety?: string
  sex?: string
  body?: string
  age?: string
  days?: DayBandKey
  /** A lower bound: this band and every band above it. Ignored when `days` is set. */
  daysFrom?: DayBandKey
  q?: string
  sort?: 'longest' | 'shortest'
}

function single(value: LocationQuery[string]): string | undefined {
  const first = Array.isArray(value) ? value[0] : value
  return typeof first === 'string' && first !== '' ? first : undefined
}

function isBand(value: string | undefined): value is DayBandKey {
  return DAY_BANDS.some((band) => band.key === value)
}

/** Read /animals' query string back into filters. Values the page cannot
 *  use (an unknown kind, a band that no longer exists) are dropped rather
 *  than guessed at, so a stale link shows more animals, never the wrong ones.
 *  County, shelter and variety are free text and are checked against the
 *  data by the page. */
export function parseAnimalQuery(query: LocationQuery): AnimalQuery {
  const kindParam = single(query.kind)
  const sex = single(query.sex)
  const body = single(query.body)
  const age = single(query.age)
  const days = single(query.days)
  const daysFrom = single(query.daysFrom)
  const sort = single(query.sort)
  return {
    kind: kindParam ? KIND_FROM_PARAM[kindParam] : undefined,
    county: single(query.county),
    shelter: single(query.shelter),
    variety: single(query.variety),
    sex: sex && sex in SEX_LABEL ? sex : undefined,
    body: body && body in BODY_LABEL ? body : undefined,
    age: age && age in AGE_LABEL ? age : undefined,
    // A band and a lower bound describe the same control; the exact band wins.
    days: isBand(days) ? days : undefined,
    daysFrom: !isBand(days) && isBand(daysFrom) ? daysFrom : undefined,
    q: single(query.q)?.trim() || undefined,
    sort: sort === 'shortest' ? 'shortest' : undefined,
  }
}

export function animalsLink(query: AnimalQuery) {
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === '') continue
    out[key] = key === 'kind' ? KIND_PARAM[value as Kind] : String(value)
  }
  return { path: '/animals', query: out }
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2)
}

/** Count per key, largest first; ties broken by name so the order is stable. */
export function tally<T>(items: T[], key: (item: T) => string): [string, number][] {
  const counts = new Map<string, number>()
  for (const item of items) {
    const name = key(item)
    counts.set(name, (counts.get(name) ?? 0) + 1)
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-TW'))
}


export function formatCount(value: number): string {
  return value.toLocaleString('zh-TW')
}
