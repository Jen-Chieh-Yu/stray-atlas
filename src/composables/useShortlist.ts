import { computed, ref } from 'vue'
import { taipeiToday } from '@/lib/days'
import { STORAGE_KEY, entryFor, parseStored } from '@/lib/shortlist'
import type { ShortlistEntry } from '@/lib/shortlist'
import type { Animal } from '@/types'

/** The shortlist, one copy for the whole page: the cards, the dialog, the
 *  top bar's count and /shortlist all read and change the same list.
 *
 *  localStorage can be missing or refuse (a private window, blocked site
 *  data, a full quota), so every read and write is wrapped and a failure
 *  leaves an empty list that still works for the visit. Another tab's change
 *  arrives through the storage event.
 *
 *  Used by: App.vue, AnimalCard.vue, AnimalDialog.vue and ShortlistView.vue. */

function load(): ShortlistEntry[] {
  try {
    return parseStored(window.localStorage.getItem(STORAGE_KEY))
  } catch {
    return []
  }
}

const entries = ref<ShortlistEntry[]>(typeof window === 'undefined' ? [] : load())

function save() {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.value))
  } catch {
    // Kept for this visit only; there is nowhere else to put it.
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEY) entries.value = parseStored(event.newValue)
  })
}

const ids = computed(() => new Set(entries.value.map((entry) => entry.id)))

export function useShortlist() {
  function has(id: string): boolean {
    return ids.value.has(id)
  }

  function add(animal: Animal, shelterName: string, snapshotDate: string) {
    if (has(animal.id)) return
    entries.value = [...entries.value, entryFor(animal, shelterName, snapshotDate, taipeiToday())]
    save()
  }

  /** The entry and where it was, for 復原. */
  function remove(id: string): { entry: ShortlistEntry; index: number } | null {
    const index = entries.value.findIndex((entry) => entry.id === id)
    if (index < 0) return null
    const entry = entries.value[index]
    entries.value = entries.value.filter((_, at) => at !== index)
    save()
    return { entry, index }
  }

  function restore(entry: ShortlistEntry, index: number) {
    if (has(entry.id)) return
    const next = [...entries.value]
    next.splice(Math.min(index, next.length), 0, entry)
    entries.value = next
    save()
  }

  function toggle(animal: Animal, shelterName: string, snapshotDate: string) {
    if (has(animal.id)) remove(animal.id)
    else add(animal, shelterName, snapshotDate)
  }

  function clear() {
    entries.value = []
    save()
  }

  return {
    entries,
    count: computed(() => entries.value.length),
    has,
    toggle,
    remove,
    restore,
    clear,
  }
}
