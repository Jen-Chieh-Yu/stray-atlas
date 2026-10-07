import type { LocationQuery } from 'vue-router'
import type { Animal, Kind } from '@/types'

/* Animal helpers shared across pages.
 *
 *  Used by: HomeView.vue and AnimalsView.vue (labels, day bands, the /animals
 *  query contract, counting helpers), ShelterListView.vue, ShelterView.vue
 *  and MapView.vue (link builder, formatCount, median), and AnalysisView.vue,
 *  AboutView.vue, AnimalCard.vue and ShelterSpark.vue (formatCount; SEX_LABEL
 *  on the card). The search-by-number helpers are used by HomeView.vue,
 *  AnimalsView.vue and ShelterView.vue; the word search, its synonyms and
 *  the age, colour and sterilization codes by AnimalsView.vue; pickSiblings
 *  by AnimalDialog.vue; OFFICIAL_ADOPTION_URL by App.vue, AboutView.vue,
 *  AnimalsView.vue and MissingAnimalDialog.vue; SHELTER_SYSTEM_URL by
 *  AboutView.vue; LOST_PET_LINKS by AnimalsView.vue; the 開放認養日 helpers
 *  by AnimalCard.vue and AnimalDialog.vue; and rosterHint by AnimalsView.vue.
 */

/** Display labels for the coded columns. One copy, shared by every page. */
export const SEX_LABEL: Record<string, string> = { M: '公', F: '母', N: '未填' }
export const BODY_LABEL: Record<string, string> = { SMALL: '小型', MEDIUM: '中型', BIG: '大型' }
/** N is the find-animals page's code for an age or a sterilization the
 *  shelter left blank: a group of its own, never folded into another (an
 *  unrecorded sterilization is not 未絕育). The data writes a blank age as ''. */
export const AGE_LABEL: Record<string, string> = { CHILD: '幼體', ADULT: '成體', N: '未填' }
export const STERILIZED_LABEL: Record<string, string> = { T: '已絕育', F: '未絕育', N: '未填' }

export function ageCode(animal: Pick<Animal, 'age'>): string {
  return animal.age || 'N'
}

/** What the colour filter calls a blank 毛色. */
export const NO_COLOUR = '未填'

export function colourOf(animal: Pick<Animal, 'colour'>): string {
  return animal.colour || NO_COLOUR
}

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
  /** 毛色 as the data writes it, or NO_COLOUR; checked against the data by
   *  the page, like variety. */
  colour?: string
  sterilized?: string
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
  const sterilized = single(query.sterilized)
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
    colour: single(query.colour),
    sterilized: sterilized && sterilized in STERILIZED_LABEL ? sterilized : undefined,
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

/** The ministry's adoption listing, built on the same feed. Where to send
 *  someone whose animal this site no longer lists. */
export const OFFICIAL_ADOPTION_URL =
  'https://www.pet.gov.tw/AnimalApp/AnnounceMent.aspx?PageType=Adopt'

/** 全國動物收容管理系統, the ministry's shelter system on pet.gov.tw, at its
 *  收容公告 page; the page is titled with the system's name. The roster and
 *  the photos are published through it. */
export const SHELTER_SYSTEM_URL = 'https://www.pet.gov.tw/AnimalApp/AnnounceMent_Announce.aspx'

/** Where to look for a lost pet, for the note on the find-animals page
 *  (DESIGN.md §6). Each opened and checked 2026-10-07:
 *  - announcements: 收容公告 in the national shelter system, the animals
 *    just taken in, filterable by 收容所縣市 and 收容所
 *  - report: 遺失申報, for a registered pet; asks for the owner's ID number
 *    and the chip number, and posts the pet for a nationwide search
 *  - counties: the two counties with a claim page of their own. */
export const LOST_PET_LINKS = {
  announcements: SHELTER_SYSTEM_URL,
  report: 'https://www.pet.gov.tw/Web/O205.aspx',
  counties: [
    { county: '新北市', url: 'https://act-adopt.ahiqo.ntpc.gov.tw/?AdoptionOnOff=2' },
    { county: '臺中市', url: 'https://www.animal.taichung.gov.tw/1521448/1521481/1521494' },
  ],
}

/* ── 開放認養日 ────────────────────────────────────────────────────────────── */

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/

/** True when the shelter's 開放認養日 falls after the snapshot. Measured
 *  against the snapshot, never today, like 已在所: the page shows that day's
 *  roster. Both are YYYY-MM-DD, so string order is date order. */
export function opensAfter(opendate: string, snapshotDate: string): boolean {
  return ISO_DATE.test(opendate) && ISO_DATE.test(snapshotDate) && opendate > snapshotDate
}

/** 2026-10-05 → 10/05, for a badge. */
export function monthDay(date: string): string {
  return `${date.slice(5, 7)}/${date.slice(8, 10)}`
}

/** 2026-10-05 → 10 月 5 日, for a sentence. */
export function monthDayLong(date: string): string {
  return `${Number(date.slice(5, 7))} 月 ${Number(date.slice(8, 10))} 日`
}

/** The loading line's hint on pages that wait for the whole roster: what is
 *  loading, counted from home.json. Without it the line names the data and
 *  leaves the count out, rather than showing a stale one. No size: the
 *  compressed download depends on GitHub Pages, not on this site, and an
 *  estimate of it was judged not worth stating (2026-10-01). */
export function rosterHint(roster?: { count: number }): string {
  if (!roster) return '全國動物資料'
  return `全國 ${formatCount(roster.count)} 隻動物的資料`
}

/* ── Search by number ──────────────────────────────────────────────────────
 * Someone who saw an animal at the shelter or on pet.gov.tw has its 收容編號
 * and nothing else. The formats differ by shelter (AAAHG1141003002,
 * W150910-14, 107-E015D), so "looks like a number" is the only rule that
 * covers them: a digit, no Han character, no space. */

const HAN = /\p{Script=Han}/u

export function isIdQuery(text: string | undefined): boolean {
  return !!text && /\d/.test(text) && !HAN.test(text) && !/\s/.test(text)
}

/** Whole-value match on 收容編號 or 流水號, ignoring case. Never a substring:
 *  a fragment such as 1141003 hits hundreds of animals, which helps nobody
 *  looking for one. */
export function matchesId(animal: Pick<Animal, 'id' | 'subid'>, text: string): boolean {
  const needle = text.toUpperCase()
  return animal.subid.toUpperCase() === needle || animal.id === needle
}

/** Where a submitted search goes. A number clears every other filter, since
 *  whoever typed it wants that one animal and a leftover 狗 or county would
 *  only turn it into a misleading "not found"; a single hit opens its dialog
 *  straight away. Any other text keeps the filters it was typed under. */
export function searchLink(
  text: string,
  keep: AnimalQuery,
  animals: Pick<Animal, 'id' | 'subid'>[],
) {
  const q = text.trim()
  if (!isIdQuery(q)) return animalsLink({ ...keep, q: q || undefined })
  const link = animalsLink({ q })
  const hits = animals.filter((animal) => matchesId(animal, q))
  if (hits.length === 1) link.query.animal = hits[0].id
  return link
}

/* ── Words people search with that the data does not use ──────────────────
 * Each adds to what the word already matches, never replaces it: 賓士 still
 * finds the one cat recorded as the breed 賓士貓. 台灣犬 is deliberately
 * absent: it is a breed the shelters record (eight dogs on 2026-10-07), so it
 * is matched as written. Shelters write orange as 黃; 橘貓 takes in 黃白色,
 * the orange-and-white cats most people also call 橘貓 (decided 2026-10-07),
 * and leaves out 黑黃色, which on a cat is mostly tortoiseshell. Colours need
 * no entry of their own (虎斑, 三花): the search reads the colour too. */

type Searchable = Pick<Animal, 'kind' | 'variety' | 'colour'>

export interface SearchSynonym {
  word: string
  /** How the applied-filter tag explains it. */
  means: string
  matches: (animal: Searchable) => boolean
}

const ORANGE = new Set(['黃色', '黃虎斑色', '黃白色'])
const isMixed = (animal: Searchable) => animal.variety.includes('混種')

export const SEARCH_SYNONYMS: SearchSynonym[] = [
  { word: '米克斯', means: '品種含「混種」', matches: isMixed },
  { word: '土狗', means: '狗，品種含「混種」', matches: (a) => a.kind === '狗' && isMixed(a) },
  { word: '土貓', means: '貓，品種含「混種」', matches: (a) => a.kind === '貓' && isMixed(a) },
  {
    word: '橘貓',
    means: '貓，毛色黃色、黃虎斑色或黃白色',
    matches: (a) => a.kind === '貓' && ORANGE.has(a.colour),
  },
  {
    word: '賓士',
    means: '貓，毛色黑白色',
    matches: (a) => a.kind === '貓' && a.colour === '黑白色',
  },
]

const SYNONYM_BY_WORD = new Map(SEARCH_SYNONYMS.map((synonym) => [synonym.word, synonym]))

/** Search text that is not a number: every word must appear in the place
 *  (county and shelter), the variety or the colour, or be a synonym whose
 *  meaning the animal fits. */
export function matchesWords(animal: Searchable, place: string, text: string): boolean {
  const haystack = `${place} ${animal.variety} ${animal.colour}`
  return text
    .split(/\s+/)
    .every((word) => haystack.includes(word) || !!SYNONYM_BY_WORD.get(word)?.matches(animal))
}

/** The applied-filter tag for a search, naming what any synonym stood for so
 *  nobody takes 8,000 米克斯 for a literal match. */
export function searchTagLabel(q: string): string {
  if (isIdQuery(q)) return `編號「${q}」`
  const used = q.split(/\s+/).flatMap((word) => SYNONYM_BY_WORD.get(word) ?? [])
  if (used.length === 0) return `搜尋「${q}」`
  if (used.length === 1 && used[0].word === q) return `搜尋「${q}」＝${used[0].means}`
  return `搜尋「${q}」（${used.map((synonym) => `${synonym.word}＝${synonym.means}`).join('；')}）`
}

/** True when a 流水號 is larger than every one in the roster, i.e. the animal
 *  was probably registered after this snapshot. Only 流水號 are sequential;
 *  收容編號 follow each shelter's own scheme and say nothing about age. */
export function isNewerId(id: string, animals: Pick<Animal, 'id'>[]): boolean {
  if (!/^\d+$/.test(id)) return false
  let largest = -1
  for (const animal of animals) {
    const value = Number(animal.id)
    if (value > largest) largest = value
  }
  return largest >= 0 && Number(id) > largest
}

/** Up to `count` animals in random order, those with a photo first: a strip
 *  of grey circles would defeat its purpose. The ones without a photo are
 *  only used to fill up, and remain in the full list one link away. */
export function pickSiblings<T extends Pick<Animal, 'photo'>>(
  pool: T[],
  count: number,
  random: () => number = Math.random,
): T[] {
  const shuffled = [...pool]
  for (let index = shuffled.length - 1; index > 0; index--) {
    const other = Math.floor(random() * (index + 1))
    ;[shuffled[index], shuffled[other]] = [shuffled[other], shuffled[index]]
  }
  const withPhoto = shuffled.filter((animal) => animal.photo)
  const without = shuffled.filter((animal) => !animal.photo)
  return [...withPhoto, ...without].slice(0, count)
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2)
}

/** Add up [key, count] pairs key by key, keeping first-seen order. */
export function sumCounts(entries: Iterable<[string, number]>): Map<string, number> {
  const counts = new Map<string, number>()
  for (const [name, count] of entries) counts.set(name, (counts.get(name) ?? 0) + count)
  return counts
}

/** Counts largest first; ties broken by name so the order is stable. The
 *  home page ranks the counts in home.json with this, rather than taking an
 *  order from Python, which cannot reproduce zh-TW collation. */
export function rank(counts: Iterable<[string, number]>): [string, number][] {
  return [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-TW'))
}

/** Count per key, ranked. */
export function tally<T>(items: T[], key: (item: T) => string): [string, number][] {
  return rank(sumCounts(items.map((item): [string, number] => [key(item), 1])))
}

export function formatCount(value: number): string {
  return value.toLocaleString('zh-TW')
}
