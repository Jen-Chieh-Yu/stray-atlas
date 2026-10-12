import { ref } from 'vue'
import { snapshotAge } from '@/lib/days'
import type { Shelter, ShelterInfo } from '@/types'

/* Shelter helpers: tidy the address and phone fields the source hands over,
 * build the Google Maps links for the shelter introduction page, read the
 * hand-kept visitor information, and hold the shelter list's view choice.
 *
 *  Used by: MapView.vue, ShelterListView.vue, ShelterView.vue and
 *  ShortlistView.vue.
 */

/** The shelter list's layout: card grid or full-width rows. It lives here,
 *  at module scope, rather than in the page, so the choice survives a trip
 *  to a shelter page and back within the visit without going into the URL;
 *  a reload starts from the grid again. */
export const shelterListView = ref<'grid' | 'list'>('grid')

export interface CleanAddress {
  /** What the page shows. */
  text: string
  /** The field as the source has it, for the hover title. */
  raw: string
  /** Coordinates the source typed into the address field, if any. */
  coords: { lat: number; lng: number } | null
}

const MAP_LINK = /[(（]\s*地圖[:：].*?[)）]/g
const COORDS = /[(（][^()（）]*?座標[^()（）]*?(\d{2}\.\d+)\s*[,，、]\s*(\d{3}\.\d+)[^()（）]*[)）]/

/** Strip what does not belong in an address and keep what helps a visitor.
 *
 *  Three shelters carry machine fields in the address column: a map short
 *  link (two 苗栗 records) and a coordinate pair (彰化臨時收容所). Those are
 *  removed from the text; the coordinates are kept for the map. Landmark
 *  notes in brackets (「龍巖人本旁」「屏東科技大學內」) are real directions
 *  and stay. */
export function cleanAddress(raw: string): CleanAddress {
  const match = raw.match(COORDS)
  const coords = match ? { lat: Number(match[1]), lng: Number(match[2]) } : null
  const text = raw.replace(MAP_LINK, '').replace(COORDS, '').trim()
  return { text, raw, coords }
}

/** Two spellings of one place (善化站's 1-19 and 1~19, full-width slashes in
 *  a pasted URL) should count as one address; two different places (瑞芳)
 *  should not. The key folds exactly those differences and nothing else. */
function sameKey(text: string): string {
  return text.normalize('NFKC').replace(/[~～]/g, '-').replace(/\s+/g, '')
}

/** Every distinct address, cleaned, in source order. */
export function addressesOf(shelter: Pick<Shelter, 'addresses'>): CleanAddress[] {
  const seen = new Set<string>()
  const out: CleanAddress[] = []
  for (const raw of shelter.addresses) {
    const clean = cleanAddress(raw)
    const key = sameKey(clean.text)
    if (seen.has(key)) continue
    seen.add(key)
    out.push(clean)
  }
  return out
}

/** How many spellings the source had beyond the distinct places. */
export function duplicateSpellings(shelter: Pick<Shelter, 'addresses'>): number {
  return shelter.addresses.length - addressesOf(shelter).length
}

/** Whether the source bracket note was a machine field that the page drops. */
export function hasMachineField(shelter: Shelter): boolean {
  return shelter.addresses.some((raw) => cleanAddress(raw).text !== raw.trim())
}

/** A tel: link, or null when there are too few digits to dial. An extension
 *  written 分機 or 轉 follows a comma, which phones dial after a pause. */
export function dialHref(text: string): string | null {
  const [main, extension = ''] = text.split(/分機|轉/)
  const digits = main.replace(/[^0-9]/g, '')
  if (digits.length < 7) return null
  const ext = extension.replace(/[^0-9]/g, '')
  return `tel:${digits}${ext ? `,${ext}` : ''}`
}

/** A number is usable when it has enough digits to dial. Two records carry a
 *  bare area code, "(09)" and "(72)"; those are shown as incomplete. */
export function phoneOf(shelter: Pick<Shelter, 'tel'>): { text: string; href: string | null } {
  return { text: shelter.tel, href: dialHref(shelter.tel) }
}

/* ── Visitor information (data/reference/shelter-info.json) ────────────── */

/** After this long without anyone reading the sources again, the page says
 *  the hours may be out of date. Measured from the reader's today, not the
 *  snapshot: this file does not change with the feed. */
export const INFO_STALE_AFTER_DAYS = 180

export function infoIsStale(info: Pick<ShelterInfo, 'checked'>, now: Date = new Date()): boolean {
  const age = snapshotAge(info.checked, now)
  return age !== null && age > INFO_STALE_AFTER_DAYS
}

export const VISIT_LABEL: Record<NonNullable<ShelterInfo['visit']>, string> = {
  appointment: '須先預約',
  'walk-in': '可直接前往',
  unstated: '官方未說明',
}

/** Whether a shortlist row should send the visitor to the shelter page
 *  before phoning: the hours are disputed, missing or old. */
export function infoNeedsCall(info: ShelterInfo | undefined, now: Date = new Date()): boolean {
  if (!info) return false
  return Boolean(info.caution) || !info.hours || infoIsStale(info, now)
}

/** Coordinates when the source has them; otherwise the address without its
 *  bracketed directions, which help a visitor but confuse the geocoder. */
function mapQuery(address: CleanAddress): string {
  if (address.coords) return `${address.coords.lat},${address.coords.lng}`
  return address.text.replace(/[(（][^()（）]*[)）]/g, '').trim()
}

/** The embed key comes from the build environment (VITE_GOOGLE_MAPS_EMBED_KEY).
 *  It is visible in the shipped page by design; it must be restricted to this
 *  site's referrers in Google Cloud. Without it the page shows the open-in-
 *  Google-Maps link only. */
const EMBED_KEY = import.meta.env.VITE_GOOGLE_MAPS_EMBED_KEY?.trim() ?? ''

export const hasMapEmbed = EMBED_KEY !== ''

/** Maps Embed API, place mode. Free with no usage cap, but it needs a key. */
export function mapEmbedUrl(address: CleanAddress): string | null {
  if (!hasMapEmbed) return null
  const params = new URLSearchParams({
    key: EMBED_KEY,
    q: mapQuery(address),
    language: 'zh-TW',
    region: 'TW',
  })
  return `https://www.google.com/maps/embed/v1/place?${params}`
}

/** A plain Maps URL: needs no key and opens the app on phones. */
export function mapOpenUrl(address: CleanAddress): string {
  const params = new URLSearchParams({ api: '1', query: mapQuery(address) })
  return `https://www.google.com/maps/search/?${params}`
}

/** 北 to 南: the source's area code follows that order (2 臺北市 … 23 連江縣). */
export function northToSouth(shelter: Shelter): number {
  return Number(shelter.area_pkid) || 99
}
