import { computed, onMounted, ref } from 'vue'
import { daysInShelter, fetchAnimals, fetchShelters } from '@/composables/useAtlasData'
import type { Animal, Shelter } from '@/types'

/** Every animal and shelter, plus the per-animal numbers the cards show.
 *
 *  Shared by the home page and the find-animals page so both rank an animal
 *  the same way. The two files are fetched once per visit (useAtlasData
 *  caches the promises), so a second caller costs nothing.
 *
 *  Used by: HomeView.vue and AnimalsView.vue.
 */
export function useRoster() {
  const animals = ref<Animal[]>([])
  const shelters = ref<Shelter[]>([])
  const snapshotDate = ref('')
  const loading = ref(true)
  const error = ref<string | null>(null)

  onMounted(async () => {
    try {
      const [payload, everyAnimal] = await Promise.all([fetchShelters(), fetchAnimals()])
      snapshotDate.value = payload.snapshot_date
      shelters.value = payload.shelters
      animals.value = everyAnimal
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : String(cause)
    } finally {
      loading.value = false
    }
  })

  const shelterById = computed(
    () => new Map(shelters.value.map((shelter) => [shelter.id, shelter])),
  )

  function placeOf(animal: Animal): string {
    return shelterById.value.get(animal.shelter)?.name ?? ''
  }

  function countyOf(animal: Animal): string {
    return shelterById.value.get(animal.shelter)?.county ?? ''
  }

  const daysById = computed(
    () =>
      new Map(
        animals.value.map((animal) => [animal.id, daysInShelter(animal.created, snapshotDate.value)]),
      ),
  )

  function daysOf(animal: Animal): number | null {
    return daysById.value.get(animal.id) ?? null
  }

  const knownDays = computed(() =>
    [...daysById.value.values()]
      .filter((value): value is number => value !== null)
      .sort((a, b) => a - b),
  )

  /** Share of the snapshot that has been in for strictly fewer days. It ranks
   *  an animal against the others still in the shelter today, which is all a
   *  stock snapshot can rank against (CLAUDE.md §1.3). */
  function percentileOf(animal: Animal): number {
    const value = daysOf(animal)
    const sorted = knownDays.value
    if (value === null || sorted.length === 0) return 0
    let low = 0
    let high = sorted.length
    while (low < high) {
      const mid = (low + high) >> 1
      if (sorted[mid] < value) low = mid + 1
      else high = mid
    }
    return (low / sorted.length) * 100
  }

  /** Longest stay first. Sorted explicitly rather than trusting the file order. */
  const byLongest = computed(() =>
    animals.value
      .filter((animal) => daysOf(animal) !== null)
      .sort((a, b) => (daysOf(b) ?? 0) - (daysOf(a) ?? 0)),
  )

  /** The single longest stay, which its card names outright. */
  const longestId = computed(() => byLongest.value[0]?.id ?? null)

  return {
    animals,
    shelters,
    snapshotDate,
    loading,
    error,
    shelterById,
    placeOf,
    countyOf,
    daysOf,
    knownDays,
    percentileOf,
    byLongest,
    longestId,
  }
}
