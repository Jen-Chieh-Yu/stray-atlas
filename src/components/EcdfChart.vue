<script setup lang="ts">
/** Cumulative share of animals against days in the shelter, 狗 versus 貓.
 *
 *  Paired with the KDE deliberately. The density's shape is an argument about
 *  the bandwidth; this curve has no bandwidth and no smoothing, so every figure
 *  quoted in the surrounding prose is read off here instead. The x axis
 *  follows the page's log / linear setting.
 *
 *  Used by: AnalysisView.vue.
 */
import { computed, ref } from 'vue'
import { axisTicks, labelDays } from '@/lib/days'
import type { Scale } from '@/types'

const props = defineProps<{
  series: { key: string; label: string; colour: string; points: [number, number][] }[]
  maxDays: number
  ticks: number[]
  scale: Scale
}>()

const W = 900
const H = 330
const PAD = { top: 18, right: 18, bottom: 38, left: 56 }
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom
const bottom = PAD.top + plotH

function toAxis(days: number): number {
  return props.scale === 'log' ? Math.log10(Math.max(days, 0.5)) : days
}

const lo = computed(() => toAxis(props.scale === 'log' ? 0.5 : 0))
const hi = computed(() => toAxis(props.maxDays))

function x(days: number): number {
  return PAD.left + ((toAxis(days) - lo.value) / (hi.value - lo.value)) * plotW
}

function y(share: number): number {
  return bottom - share * plotH
}

/** Step, not line: the ECDF jumps at each observation and does not interpolate
 *  between two animals. Drawing it as a slope would claim values nobody had.
 *  Each curve runs flat to the right edge once it reaches its last animal. */
const paths = computed(() =>
  props.series.map((s) => {
    let d = ''
    let previous = 0
    s.points.forEach((p, i) => {
      const px = x(p[0]).toFixed(1)
      if (i === 0) d += `M${px},${y(0).toFixed(1)}`
      else d += ` L${px},${y(previous).toFixed(1)}`
      d += ` L${px},${y(p[1]).toFixed(1)}`
      previous = p[1]
    })
    d += ` L${x(props.maxDays).toFixed(1)},${y(previous).toFixed(1)}`
    return { key: s.key, colour: s.colour, d }
  }),
)

const gridShares = [0, 0.25, 0.5, 0.75, 1]

/** The two thresholds the prose quotes: over one year, over four. */
const references = computed(() =>
  [
    { days: 365, label: '1 年' },
    { days: 1460, label: '4 年' },
  ].filter((mark) => mark.days <= props.maxDays),
)

const tickMarks = computed(() =>
  axisTicks(props.scale, props.ticks)
    .filter((tick) => tick.days <= props.maxDays)
    .map((tick) => ({ at: x(tick.days), label: tick.label })),
)

const cursor = ref<number | null>(null)

function onMove(event: MouseEvent) {
  const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect()
  const px = ((event.clientX - rect.left) / rect.width) * W
  cursor.value = Math.min(PAD.left + plotW, Math.max(PAD.left, px))
}

const cursorDays = computed(() => {
  if (cursor.value === null) return null
  const value = lo.value + ((cursor.value - PAD.left) / plotW) * (hi.value - lo.value)
  return Math.round(props.scale === 'log' ? Math.pow(10, value) : value)
})

/** The share at or below the cursor, per series, by walking the thinned points. */
const readout = computed(() => {
  const limit = cursorDays.value
  if (limit === null) return []
  return props.series.map((s) => {
    let share = 0
    for (const [days, value] of s.points) {
      if (days > limit) break
      share = value
    }
    return { key: s.key, label: s.label, colour: s.colour, share }
  })
})
</script>

<template>
  <figure class="chart">
    <div class="frame">
      <svg
        :viewBox="`0 0 ${W} ${H}`"
        role="img"
        :aria-label="`狗與貓在所天數的累積分布，${scale === 'log' ? '對數' : '線性'}橫軸`"
        @mousemove="onMove"
        @mouseleave="cursor = null"
      >
        <template v-for="share in gridShares" :key="`g${share}`">
          <line class="gridline" :x1="PAD.left" :x2="W - PAD.right" :y1="y(share)" :y2="y(share)" />
          <text class="label" :x="PAD.left - 8" :y="y(share) + 4" text-anchor="end">
            {{ Math.round(share * 100) }}%
          </text>
        </template>

        <template v-for="mark in references" :key="`r${mark.days}`">
          <line class="reference" :x1="x(mark.days)" :x2="x(mark.days)" :y1="PAD.top" :y2="bottom" />
          <text class="label" :x="x(mark.days) + 5" :y="PAD.top + 12">{{ mark.label }}</text>
        </template>

        <path
          v-for="p in paths"
          :key="p.key"
          class="line"
          :d="p.d"
          :style="{ stroke: p.colour }"
        />

        <g class="axis">
          <line :x1="PAD.left" :x2="W - PAD.right" :y1="bottom" :y2="bottom" />
          <template v-for="tick in tickMarks" :key="`t${tick.at}`">
            <line :x1="tick.at" :x2="tick.at" :y1="bottom" :y2="bottom + 4" />
            <text :x="tick.at" :y="bottom + 18" text-anchor="middle">{{ tick.label }}</text>
          </template>
          <text :x="PAD.left" :y="PAD.top - 4">累積比例</text>
        </g>

        <template v-if="cursor !== null">
          <line class="cursor" :x1="cursor" :x2="cursor" :y1="PAD.top" :y2="bottom" />
          <circle
            v-for="r in readout"
            :key="`c${r.key}`"
            :cx="cursor"
            :cy="y(r.share)"
            r="4.5"
            :style="{ fill: r.colour }"
          />
        </template>
      </svg>
    </div>

    <figcaption v-if="cursorDays !== null" class="readout">
      <strong>{{ labelDays(cursorDays) }}以內</strong>
      <span v-for="r in readout" :key="r.key">
        {{ r.label }} {{ (r.share * 100).toFixed(1) }}%
      </span>
    </figcaption>
    <figcaption v-else class="readout muted">滑過任一位置可讀出該天數以內的累積比例。</figcaption>
  </figure>
</template>

<style scoped>
.chart {
  margin: 0;
}

.frame {
  overflow-x: auto;
}

svg {
  display: block;
  width: 100%;
  min-width: 560px;
  height: auto;
}

.gridline {
  stroke: var(--hairline);
  stroke-dasharray: 2 4;
}

.reference {
  stroke: var(--ink);
  stroke-width: 1.2;
  stroke-dasharray: 4 4;
}

.label {
  fill: var(--ink-muted);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.line {
  fill: none;
  stroke-width: 2;
  stroke-linejoin: round;
}

.axis line {
  stroke: var(--hairline);
}

.axis text {
  fill: var(--ink-muted);
  font-size: 11px;
}

.cursor {
  stroke: var(--ink-muted);
  stroke-width: 1;
}

.readout {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  align-items: baseline;
  min-height: 1.4rem;
  margin-top: 0.4rem;
  color: var(--ink-secondary);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}

.readout.muted {
  color: var(--ink-muted);
}
</style>
