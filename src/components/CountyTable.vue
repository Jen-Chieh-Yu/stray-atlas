<script setup lang="ts">
import type { CountyStats, Metric } from '@/types'

defineProps<{
  rows: { county: CountyStats; value: number | null }[]
  metric: Metric
  max: number
  selected: string | null
}>()

const emit = defineEmits<{ hover: [string | null]; select: [string | null] }>()

function format(value: number | null, metric: Metric): string {
  if (value === null) return '—'
  return metric === 'count' ? value.toLocaleString('zh-TW') : `${value.toLocaleString('zh-TW')} 天`
}
</script>

<template>
  <!-- Doubles as the table view the chart owes: every value is readable as a
       number, so nothing depends on distinguishing two shades of orange. -->
  <ol class="ranked" @mouseleave="emit('hover', null)">
    <li
      v-for="row in rows"
      :key="row.county.pkid"
      :class="{ row: true, active: selected === row.county.name }"
      @mouseenter="emit('hover', row.county.name)"
      @click="emit('select', selected === row.county.name ? null : row.county.name)"
    >
      <span class="name">
        <span v-if="selected === row.county.name" class="dot" aria-hidden="true" />{{
          row.county.name
        }}
      </span>
      <span class="bar-track">
        <span
          class="bar"
          :style="{ width: `${row.value === null || max === 0 ? 0 : (row.value / max) * 100}%` }"
        />
      </span>
      <span class="value">{{ format(row.value, metric) }}</span>
    </li>
  </ol>
</template>

<style scoped>
.ranked {
  list-style: none;
  margin: 0;
  padding: 0;
}

.row {
  display: grid;
  grid-template-columns: 4.5rem 1fr 5rem;
  align-items: center;
  gap: 0.75rem;
  padding: 0.22rem 0.5rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 120ms ease;
}

.row:hover,
.row.active {
  background: var(--surface-sunk);
}

.row.active .name,
.row.active .value {
  color: var(--accent-text);
  font-weight: 600;
}

.dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--accent-text);
  margin-right: 0.3rem;
  vertical-align: middle;
}

.name {
  font-size: 0.9rem;
  color: var(--ink-secondary);
}

.bar-track {
  height: 10px;
  background: var(--surface-sunk);
  border-radius: 999px;
  overflow: hidden;
}

.bar {
  display: block;
  height: 100%;
  /* 4px rounded data-end, anchored to the baseline at the left. */
  border-radius: 0 4px 4px 0;
  background: var(--ramp-4);
}

.value {
  font-size: 0.9rem;
  text-align: right;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
</style>
