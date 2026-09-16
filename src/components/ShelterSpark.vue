<script setup lang="ts">
import { computed } from 'vue'
import { formatCount } from '@/lib/animals'

/** Seven bars, one per stay band, all in one colour: the x axis is already
 *  ordered, so colouring it again would say the same thing twice. Empty bands
 *  draw as a flat --no-data line, the map's colour for "nothing here".
 *
 *  Used by: ShelterListView.vue (compact) and ShelterView.vue (large, every
 *  band labelled). */
const props = defineProps<{
  histogram: number[]
  labels: string[]
  large?: boolean
}>()

const peak = computed(() => Math.max(1, ...props.histogram))

const summary = computed(() =>
  props.histogram
    .map((count, index) => `${props.labels[index] ?? ''} ${formatCount(count)} 隻`)
    .join('、'),
)
</script>

<template>
  <div :class="['spark', { large }]">
    <div class="bars" role="img" :aria-label="`在所時間分布：${summary}`">
      <i
        v-for="(count, index) in histogram"
        :key="index"
        :class="{ zero: count === 0 }"
        :style="count ? { height: `${(count / peak) * 100}%` } : undefined"
        :title="`${labels[index] ?? ''}：${formatCount(count)} 隻`"
      />
    </div>
    <div v-if="large" class="axis every">
      <span v-for="label in labels" :key="label">{{ label }}</span>
    </div>
    <div v-else class="axis">
      <span>{{ labels[0] }}</span>
      <span>{{ labels[labels.length - 1] }}</span>
    </div>
  </div>
</template>

<style scoped>
.bars {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 46px;
}

.bars i {
  display: block;
  flex: 1 1 0;
  min-width: 0;
  border-radius: 2px 2px 0 0;
  background: var(--ramp-4);
}

.bars i.zero {
  height: 3px;
  background: var(--no-data);
}

.axis {
  display: flex;
  justify-content: space-between;
  margin-top: 0.4rem;
  color: var(--ink-muted);
  font-size: 0.74rem;
}

.large .bars {
  gap: 6px;
  height: 120px;
}

.axis.every {
  display: grid;
  grid-template-columns: repeat(v-bind('histogram.length'), minmax(0, 1fr));
  gap: 6px;
  text-align: center;
}

/* Seven labels do not fit a phone; keep the two ends. */
@media (max-width: 640px) {
  .axis.every span {
    visibility: hidden;
  }

  .axis.every span:first-child,
  .axis.every span:last-child {
    visibility: visible;
    white-space: nowrap;
  }

  .axis.every span:last-child {
    text-align: right;
  }
}
</style>
