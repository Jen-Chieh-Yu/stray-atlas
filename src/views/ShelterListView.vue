<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchShelters } from '@/composables/useAtlasData'
import type { Shelter } from '@/types'

const shelters = ref<Shelter[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const county = ref<string>('all')

onMounted(async () => {
  try {
    shelters.value = (await fetchShelters()).shelters
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause)
  } finally {
    loading.value = false
  }
})

const counties = computed(() => [...new Set(shelters.value.map((s) => s.county))])

const visible = computed(() =>
  county.value === 'all'
    ? shelters.value
    : shelters.value.filter((shelter) => shelter.county === county.value),
)

const maxCount = computed(() => Math.max(...shelters.value.map((s) => s.all.count), 1))
</script>

<template>
  <div>
    <p v-if="loading" class="state">載入中…</p>
    <p v-else-if="error" class="state">收容所資料載入失敗（{{ error }}）。</p>

    <template v-else>
      <p class="intro">
        全國 {{ shelters.length }} 間公立收容所。14 個縣市只有一間，新北市有 9 間——
        點進去看該所目前仍在所的動物。
      </p>

      <div class="filter">
        <button
          type="button"
          :class="{ chip: true, small: true, on: county === 'all' }"
          @click="county = 'all'"
        >
          全部
        </button>
        <button
          v-for="name in counties"
          :key="name"
          type="button"
          :class="{ chip: true, small: true, on: county === name }"
          @click="county = name"
        >
          {{ name }}
        </button>
      </div>

      <ul class="shelters">
        <li v-for="shelter in visible" :key="shelter.id">
          <RouterLink :to="`/shelters/${shelter.id}`" class="card row">
            <div class="who">
              <span class="county-tag">{{ shelter.county }}</span>
              <span class="name">{{ shelter.name }}</span>
              <span class="addr">{{ shelter.addresses[0] }}</span>
            </div>

            <div class="figure">
              <span class="value">{{ shelter.all.count.toLocaleString('zh-TW') }}</span>
              <span class="unit">在所</span>
              <span class="bar-track">
                <span class="bar" :style="{ width: `${(shelter.all.count / maxCount) * 100}%` }" />
              </span>
            </div>

            <div class="figure">
              <span class="value">{{ shelter.all.median_days ?? '—' }}</span>
              <span class="unit">天中位數</span>
            </div>

            <div class="split">
              <span>狗 {{ shelter.狗.count }}</span>
              <span>貓 {{ shelter.貓.count }}</span>
            </div>
          </RouterLink>
        </li>
      </ul>
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

.filter {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1.25rem;
}

.shelters {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.6rem;
}

.row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 11rem 7rem 7rem;
  align-items: center;
  gap: 1rem;
  padding: 0.9rem 1.1rem;
  text-decoration: none;
  color: inherit;
  transition:
    border-color 120ms ease,
    background 120ms ease;
}

.row:hover {
  border-color: var(--ramp-3);
  background: var(--surface-sunk);
}

.who {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}

.county-tag {
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.name {
  font-weight: 600;
}

.addr {
  font-size: 0.82rem;
  color: var(--ink-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.figure {
  display: grid;
  gap: 0.2rem;
}

.value {
  font-size: 1.15rem;
  font-variant-numeric: tabular-nums;
}

.unit {
  font-size: 0.78rem;
  color: var(--ink-muted);
}

.bar-track {
  height: 6px;
  background: var(--surface-sunk);
  border-radius: 999px;
  overflow: hidden;
}

.bar {
  display: block;
  height: 100%;
  border-radius: 0 3px 3px 0;
  background: var(--ramp-4);
}

.split {
  display: grid;
  gap: 0.2rem;
  font-size: 0.85rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 820px) {
  .row {
    grid-template-columns: minmax(0, 1fr) auto;
    row-gap: 0.6rem;
  }

  .who {
    grid-column: 1 / -1;
  }
}
</style>
