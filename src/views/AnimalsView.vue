<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import AnimalGrid from '@/components/AnimalGrid.vue'
import { fetchAnimals, fetchShelters } from '@/composables/useAtlasData'
import type { Animal, Shelter } from '@/types'

const shelters = ref<Shelter[]>([])
const animals = ref<Animal[]>([])
const snapshotDate = ref('')
const loading = ref(true)
const error = ref<string | null>(null)

const county = ref('all')
const shelterId = ref('all')

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

const byId = computed(() => new Map(shelters.value.map((shelter) => [shelter.id, shelter])))

const counties = computed(() => {
  const counts = new Map<string, number>()
  for (const shelter of shelters.value) {
    counts.set(shelter.county, (counts.get(shelter.county) ?? 0) + shelter.all.count)
  }
  return [...counts.entries()]
})

/** Shelter options follow the county already chosen. Fourteen counties have
 *  exactly one shelter, so for most of the country this second control
 *  collapses to a single entry — which is itself worth seeing. */
const shelterOptions = computed(() =>
  county.value === 'all'
    ? shelters.value
    : shelters.value.filter((shelter) => shelter.county === county.value),
)

watch(county, () => {
  shelterId.value = 'all'
})

const scoped = computed(() => {
  if (shelterId.value !== 'all') {
    return animals.value.filter((animal) => animal.shelter === shelterId.value)
  }
  if (county.value !== 'all') {
    const ids = new Set(shelterOptions.value.map((shelter) => shelter.id))
    return animals.value.filter((animal) => ids.has(animal.shelter))
  }
  return animals.value
})
</script>

<template>
  <div>
    <p v-if="loading" class="state">載入中…（全國動物資料約 272 KB）</p>
    <p v-else-if="error" class="state">資料載入失敗（{{ error }}）。</p>

    <template v-else>
      <p class="intro">
        全國 {{ animals.length.toLocaleString('zh-TW') }} 隻目前仍開放認養的動物。
        先選地區縮小範圍，再用下方條件篩選。
      </p>

      <AnimalGrid :animals="scoped" :snapshot-date="snapshotDate" :shelters="byId">
        <template #scope>
          <div class="select-field">
            <label for="county">縣市位置</label>
            <select id="county" v-model="county">
              <option value="all">全部縣市（{{ animals.length.toLocaleString('zh-TW') }} 隻）</option>
              <option v-for="[name, count] in counties" :key="name" :value="name">
                {{ name }}（{{ count.toLocaleString('zh-TW') }}）
              </option>
            </select>
          </div>

          <div class="select-field">
            <label for="shelter">公立收容所</label>
            <select id="shelter" v-model="shelterId">
              <option value="all">全部收容所（{{ shelterOptions.length }} 間）</option>
              <option v-for="option in shelterOptions" :key="option.id" :value="option.id">
                {{ option.name }}（{{ option.all.count.toLocaleString('zh-TW') }}）
              </option>
            </select>
          </div>
        </template>
      </AnimalGrid>

      <section class="card caveats">
        <h2><span class="mark" aria-hidden="true">ⓘ</span> 這些卡片不能拿來說什麼（資料判讀邊界）</h2>
        <div class="cols">
          <div>
            <h3>收容所刊登照片不代表動物現況</h3>
            <p>
              照片多為入所建檔時拍攝，全國有 17.9% 的資料根本沒有照片。實際的健康與個性必須以現場互動評估為準。
            </p>
          </div>
          <div>
            <h3>「已在所天數」不是難認養程度</h3>
            <p>
              這份資料只包含尚未離所的動物，待得越久的越可能出現在其中。天數極長者常是長期醫療照護的個體，不能反推牠比較不受歡迎。
            </p>
          </div>
          <div>
            <h3>本站不辦理認養</h3>
            <p>
              這裡只呈現農業部開放資料的即時快照，不做媒合也不代辦手續。有意認養請直接洽詢該收容所，依其規定辦理。
            </p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.state {
  padding: 3rem 0;
  color: var(--ink-secondary);
}

.intro {
  margin: 0 0 1rem;
  color: var(--ink-secondary);
  max-width: 46rem;
}

.select-field {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
}

.select-field label {
  font-size: 0.85rem;
  color: var(--ink-muted);
  white-space: nowrap;
}

select {
  font: inherit;
  font-size: 0.88rem;
  padding: 0.45rem 0.7rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--hairline);
  background: var(--surface);
  color: var(--ink);
  min-width: 16rem;
  max-width: 22rem;
}

select:hover {
  border-color: var(--ramp-3);
}

.caveats {
  margin-top: 2rem;
}

.caveats h2 {
  font-size: 1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.mark {
  color: var(--accent-text);
}

.cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1.5rem;
}

.cols h3 {
  font-size: 0.9rem;
  margin-bottom: 0.35rem;
}

.cols p {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.75;
  color: var(--ink-secondary);
}
</style>
