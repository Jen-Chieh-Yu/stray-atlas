import { computed, onMounted, ref } from 'vue'
import { daysInShelter, fetchAnimals, fetchShelters } from '@/composables/useAtlasData'
import type { Animal, Shelter, ShelterPayload } from '@/types'

/** Every animal and shelter, plus the per-animal numbers the cards show.
 *
 *  Shared by the pages that list animals so each ranks an animal the same
 *  way. The two files are fetched once per visit (useAtlasData caches the
 *  promises), so a second caller costs nothing. The home page does not use
 *  this: it draws from home.json and fetches the roster afterwards.
 *
 *  Used by: AnimalsView.vue, ShelterListView.vue and ShelterView.vue.
 */
export function useRoster() {
  const animals = ref<Animal[]>([])
  const shelters = ref<Shelter[]>([])
  const snapshotDate = ref('')
  const buckets = ref<ShelterPayload['buckets']>([])
  const loading = ref(true)
  const error = ref<string | null>(null)

  onMounted(async () => {
    try {
      const [payload, everyAnimal] = await Promise.all([fetchShelters(), fetchAnimals()])
      snapshotDate.value = payload.snapshot_date
      shelters.value = payload.shelters
      buckets.value = payload.buckets
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
        animals.value.map((animal) => [
          animal.id,
          daysInShelter(animal.created, snapshotDate.value),
        ]),
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

  /** Longest stay first. Sorted explicitly rather than trusting the file order. */
  const byLongest = computed(() =>
    animals.value
      .filter((animal) => daysOf(animal) !== null)
      .sort((a, b) => (daysOf(b) ?? 0) - (daysOf(a) ?? 0)),
  )

  return {
    animals,
    shelters,
    snapshotDate,
    buckets,
    loading,
    error,
    shelterById,
    placeOf,
    countyOf,
    daysOf,
    knownDays,
    byLongest,
  }
}
