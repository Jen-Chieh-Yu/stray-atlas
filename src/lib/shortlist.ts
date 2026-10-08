import { SEX_LABEL } from '@/lib/animals'
import type { Animal, Kind } from '@/types'

/* The shortlist: animals a visitor marks to ask about, kept in this browser's
 * localStorage. No account and no server (decided 2026-10-07): the list does
 * not follow the visitor to another device, and the page says so.
 *
 * Each entry keeps the animal as it was when added, so an animal that has
 * since left the roster still has a breed, a sex and a 收容編號 to show and to
 * quote on the phone. Why it left is not in the data, so the page never says
 * 已被認養 (CLAUDE.md §1.1).
 *
 * Used by: useShortlist.ts (state and storage) and ShortlistView.vue.
 */

export const STORAGE_KEY = 'stray-atlas.shortlist.v1'

export interface ShortlistEntry {
  id: string
  subid: string
  kind: Kind
  variety: string
  sex: string
  shelter: string
  shelterName: string
  photo: string
  /** The Taipei date it was added. */
  added: string
  /** The snapshot the site was showing then. */
  snapshot: string
}

export function entryFor(
  animal: Pick<Animal, 'id' | 'subid' | 'kind' | 'variety' | 'sex' | 'shelter' | 'photo'>,
  shelterName: string,
  snapshot: string,
  added: string,
): ShortlistEntry {
  return {
    id: animal.id,
    subid: animal.subid,
    kind: animal.kind,
    variety: animal.variety,
    sex: animal.sex,
    shelter: animal.shelter,
    shelterName,
    photo: animal.photo,
    added,
    snapshot,
  }
}

const KINDS = new Set<string>(['狗', '貓', '其他'])
const TEXT_FIELDS = [
  'id',
  'subid',
  'variety',
  'sex',
  'shelter',
  'shelterName',
  'photo',
  'added',
  'snapshot',
] as const

/** Whatever is stored, read defensively: it may be from an older version,
 *  edited by hand or cut short. Rows that do not parse are dropped, and an
 *  animal listed twice is kept once. */
export function parseStored(raw: string | null): ShortlistEntry[] {
  if (!raw) return []
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return []
  }
  if (!Array.isArray(data)) return []
  const seen = new Set<string>()
  const entries: ShortlistEntry[] = []
  for (const row of data) {
    if (typeof row !== 'object' || row === null) continue
    const record = row as Record<string, unknown>
    if (!TEXT_FIELDS.every((key) => typeof record[key] === 'string')) continue
    if (typeof record.kind !== 'string' || !KINDS.has(record.kind)) continue
    const id = record.id as string
    if (!id || seen.has(id)) continue
    seen.add(id)
    entries.push(record as unknown as ShortlistEntry)
  }
  return entries
}

export interface ShortlistGroup {
  shelter: string
  name: string
  entries: ShortlistEntry[]
}

/** One group per shelter, the one with most animals first, so the phone
 *  call that covers the most comes first. Within a shelter, in the order
 *  they were added. A shelter's current name wins over the stored one. */
export function groupByShelter(
  entries: ShortlistEntry[],
  nameOf: (shelter: string) => string | undefined,
): ShortlistGroup[] {
  const groups = new Map<string, ShortlistGroup>()
  for (const entry of entries) {
    let group = groups.get(entry.shelter)
    if (!group) {
      group = {
        shelter: entry.shelter,
        name: nameOf(entry.shelter) ?? entry.shelterName,
        entries: [],
      }
      groups.set(entry.shelter, group)
    }
    group.entries.push(entry)
  }
  return [...groups.values()].sort(
    (a, b) => b.entries.length - a.entries.length || a.name.localeCompare(b.name, 'zh-TW'),
  )
}

/** 混種犬 母, as the list and the copied text name an animal. */
export function entryLabel(entry: Pick<ShortlistEntry, 'variety' | 'sex'>): string {
  const sex = entry.sex === 'M' || entry.sex === 'F' ? ` ${SEX_LABEL[entry.sex]}` : ''
  return `${entry.variety || '未填品種'}${sex}`
}

/** What 複製收容編號 hands over: plain text for a note or a message, grouped
 *  by shelter with its phone, each animal by the number a shelter asks for. */
export function shortlistText(
  groups: ShortlistGroup[],
  telOf: (shelter: string) => string | undefined,
  listed: (id: string) => boolean,
  snapshotDate: string,
): string {
  const blocks = groups.map((group) => {
    const tel = telOf(group.shelter)
    const lines = group.entries.map((entry) => {
      const number = entry.subid || `流水號 ${entry.id}`
      const gone = listed(entry.id) ? '' : '（不在目前名單）'
      return `- ${number} ${entryLabel(entry)}${gone}`
    })
    return [tel ? `${group.name} ${tel}` : group.name, ...lines].join('\n')
  })
  return [`StrayAtlas 候選清單（${snapshotDate} 資料）`, ...blocks].join('\n\n')
}
