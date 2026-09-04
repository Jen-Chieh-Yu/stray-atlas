<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AnimalGrid from '@/components/AnimalGrid.vue'
import { fetchAnimals, fetchShelters } from '@/composables/useAtlasData'
import type { Animal, Shelter } from '@/types'

const route = useRoute()
const shelter = ref<Shelter | null>(null)
const animals = ref<Animal[]>([])
const snapshotDate = ref('')
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  const id = String(route.params.id)
  try {
    const [payload, everyAnimal] = await Promise.all([fetchShelters(), fetchAnimals()])
    snapshotDate.value = payload.snapshot_date
    shelter.value = payload.shelters.find((item) => item.id === id) ?? null
    if (!shelter.value) throw new Error('查無此收容所')
    animals.value = everyAnimal.filter((animal) => animal.shelter === id)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    loading.value = false
  }
})

const mine = computed(() => animals.value)
</script>

<template>
  <div>
    <p v-if="loading" class="state">載入中…</p>

    <p v-else-if="error" class="state">
      {{ error }}。<RouterLink to="/shelters">回收容所列表</RouterLink>
    </p>

    <template v-else-if="shelter">
      <RouterLink to="/shelters" class="back">← 收容所列表</RouterLink>

      <section class="card head">
        <div>
          <p class="county-tag">{{ shelter.county }}</p>
          <h2>{{ shelter.name }}</h2>
          <p v-for="address in shelter.addresses" :key="address" class="addr">{{ address }}</p>
          <p v-if="shelter.addresses.length > 1" class="addr-note">
            來源資料對這間收容所登錄了 {{ shelter.addresses.length }} 種地址，全部列出而不擇一。
          </p>
          <p class="addr">{{ shelter.tel }}</p>
        </div>

        <dl>
          <div><dt>在所總數</dt><dd>{{ shelter.all.count.toLocaleString('zh-TW') }}</dd></div>
          <div>
            <dt>滯留中位數</dt>
            <dd class="accent">
              {{ shelter.all.median_days === null ? '—' : `${shelter.all.median_days} 天` }}
            </dd>
          </div>
          <div>
            <dt>平均滯留</dt>
            <dd>{{ shelter.all.mean_days === null ? '—' : `${shelter.all.mean_days} 天` }}</dd>
          </div>
          <div><dt>狗</dt><dd>{{ shelter.狗.count.toLocaleString('zh-TW') }}</dd></div>
          <div><dt>貓</dt><dd>{{ shelter.貓.count.toLocaleString('zh-TW') }}</dd></div>
        </dl>

        <p class="stat-note">
          中位數是這裡該讀的數字。平均值被長期滯留者拉高——這份資料只含尚未離所的動物，待越久越可能留在其中。
        </p>
      </section>

      <AnimalGrid :animals="mine" :snapshot-date="snapshotDate" />

      <section class="card caveats">
        <p>
          <strong>「已在所天數」是資料建檔至今的天數，不是這隻動物有多難認養。</strong>
          這份資料只包含尚未離所的動物，待得越久的越可能出現在其中。照片與備註由各收容所自行登錄，
          全國有 17.9% 的資料沒有照片。
        </p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.state {
  padding: 3rem 0;
  color: var(--ink-secondary);
}

.back {
  display: inline-block;
  margin-bottom: 1rem;
  color: var(--ink-secondary);
  text-decoration: none;
  font-size: 0.9rem;
}

.back:hover {
  color: var(--ink);
}

.head {
  display: flex;
  justify-content: space-between;
  gap: 2rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}

.county-tag {
  margin: 0;
  font-size: 0.8rem;
  color: var(--ink-muted);
}

.head h2 {
  font-size: 1.5rem;
  margin: 0.1rem 0 0.5rem;
}

.addr {
  margin: 0;
  font-size: 0.88rem;
  color: var(--ink-secondary);
}

.addr-note {
  margin: 0.3rem 0;
  font-size: 0.8rem;
  color: var(--ink-muted);
}

dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(6rem, auto));
  gap: 0.4rem 1.75rem;
  align-content: start;
}

dd.accent {
  color: var(--accent-text);
}

.stat-note {
  flex-basis: 100%;
  margin: 0.35rem 0 0;
  font-size: 0.76rem;
  line-height: 1.65;
  color: var(--ink-muted);
}

dl > div {
  display: grid;
  gap: 0.1rem;
}

dt {
  font-size: 0.8rem;
  color: var(--ink-muted);
}

dd {
  margin: 0;
  font-size: 1.15rem;
  font-variant-numeric: tabular-nums;
}

.caveats {
  margin-top: 1.5rem;
}

.caveats p {
  margin: 0;
  color: var(--ink-secondary);
  font-size: 0.9rem;
}

.caveats strong {
  color: var(--ink);
}
</style>
