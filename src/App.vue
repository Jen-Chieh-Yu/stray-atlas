<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useAtlasData } from '@/composables/useAtlasData'
import { useTheme } from '@/composables/useTheme'
import type { ThemeChoice } from '@/composables/useTheme'

const { stats } = useAtlasData()
const { choice: theme } = useTheme()

const THEMES: { id: ThemeChoice; label: string }[] = [
  { id: 'system', label: '系統' },
  { id: 'light', label: '淺色' },
  { id: 'dark', label: '深色' },
]
</script>

<template>
  <div class="page">
    <header class="masthead">
      <div class="masthead-text">
        <RouterLink to="/" class="wordmark"><h1>StrayAtlas 浪浪地圖</h1></RouterLink>
        <p class="lede">
          臺灣公立動物收容所目前仍開放認養的動物。
          <span v-if="stats" class="stamp">資料快照 {{ stats.snapshot_date }}</span>
        </p>
      </div>

      <fieldset class="theme">
        <legend class="sr-only">顯示模式</legend>
        <button
          v-for="option in THEMES"
          :key="option.id"
          type="button"
          :class="{ chip: true, small: true, on: theme === option.id }"
          :aria-pressed="theme === option.id"
          @click="theme = option.id"
        >
          {{ option.label }}
        </button>
      </fieldset>
    </header>

    <nav class="tabs">
      <RouterLink to="/">縣市地圖</RouterLink>
      <RouterLink to="/animals">找動物</RouterLink>
      <RouterLink to="/shelters">收容所</RouterLink>
    </nav>

    <RouterView />

    <footer class="footer">
      <p>
        資料來源：農業部「動物認領養」開放資料（<a
          href="https://data.gov.tw/dataset/85903"
          rel="noreferrer"
          target="_blank"
          >dataset 85903</a
        >），依政府資料開放授權條款第 1 版使用。行政區界線為內政部「鄉鎮市區界線」（dataset 7441）。動物照片由 pet.gov.tw 提供。
      </p>
      <p>本專案程式碼目前保留所有權利，尚未選定開放授權條款。</p>
    </footer>
  </div>
</template>

<style scoped>
.page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 3rem 1.5rem 4rem;
}

.masthead {
  margin-bottom: 1.5rem;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.wordmark {
  text-decoration: none;
}

h1 {
  font-size: clamp(1.9rem, 4vw, 2.6rem);
}

.lede {
  margin: 0.6rem 0 0;
  color: var(--ink-secondary);
  max-width: 46rem;
}

.stamp {
  display: inline-block;
  margin-left: 0.4rem;
  padding: 0.05rem 0.55rem;
  border-radius: 999px;
  background: var(--surface-sunk);
  font-size: 0.82rem;
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
}

.theme {
  border: 0;
  margin: 0;
  padding: 0;
  display: flex;
  gap: 0.3rem;
  flex-shrink: 0;
}

.tabs {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--hairline);
}

.tabs a {
  padding: 0.5rem 0.9rem;
  text-decoration: none;
  color: var(--ink-secondary);
  font-size: 0.95rem;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tabs a:hover {
  color: var(--ink);
}

.tabs a.router-link-active {
  color: var(--ink);
  border-bottom-color: var(--ramp-4);
  font-weight: 600;
}

.footer {
  margin-top: 2.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--hairline);
  color: var(--ink-muted);
  font-size: 0.85rem;
}

.footer p {
  margin: 0 0 0.4rem;
}
</style>
