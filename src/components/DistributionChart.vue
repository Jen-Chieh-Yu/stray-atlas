<script setup lang="ts">
/** Histogram with a KDE curve over it, on a switchable log10 / linear axis.
 *
 *  Bars and curve share one y axis because both are densities: the bars carry
 *  count / (n × bin width), the curve integrates to 1 over the same axis. A
 *  count axis would put them on different scales and the overlay would be a
 *  decoration rather than a comparison.
 *
 *  Used by: AnalysisView.vue.
 */
import { computed, ref } from 'vue'
import { axisTicks, labelDays } from '@/lib/days'
import type { ScaleBlock, Scale, Smoothing } from '@/types'

const props = defineProps<{
  block: ScaleBlock
  scale: Scale
  smoothing: Smoothing
  logTicks: number[]
  median: number
}>()

const W = 900
const H = 360
const PAD = { top: 18, right: 18, bottom: 38, left: 56 }
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom
const bottom = PAD.top + plotH

const curve = computed(() => props.block.kde[props.smoothing])

/** Bars stop at the largest observation; the KDE grid runs a few bandwidths
 *  past it so the curve can decay instead of being cut off. The axis has to
 *  cover both or the tail of the curve is clipped. */
const domain = computed<[number, number]>(() => {
  const bins = props.block.bins
  const points = curve.value.points
  return [bins[0].x0, Math.max(bins[bins.length - 1].x1, points[points.length - 1][0])]
})

const yMax = computed(() => {
  const bars = Math.max(...props.block.bins.map((b) => b.density))
  const line = Math.max(...curve.value.points.map((p) => p[1]))
  return Math.max(bars, line) * 1.1
})

function x(value: number): number {
  const [lo, hi] = domain.value
  return PAD.left + ((value - lo) / (hi - lo)) * plotW
}

function y(value: number): number {
  return bottom - (value / yMax.value) * plotH
}

const ticks = computed(() => {
  const [lo, hi] = domain.value
  return axisTicks(props.scale, props.logTicks)
    .map((tick) => ({
      label: tick.label,
      value: props.scale === 'log' ? Math.log10(tick.days) : tick.days,
    }))
    .filter((tick) => tick.value >= lo && tick.value <= hi)
    .map((tick) => ({ at: x(tick.value), label: tick.label }))
})

const gridShares = [0.25, 0.5, 0.75, 1]

const bars = computed(() =>
  props.block.bins.map((bin) => {
    const left = x(bin.x0)
    return {
      x: left,
      y: y(bin.density),
      // 1 unit of surface between bars.
      width: Math.max(x(bin.x1) - left - 1, 1),
      height: Math.max(bottom - y(bin.density), 0),
    }
  }),
)

const linePath = computed(() =>
  curve.value.points
    .map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`)
    .join(' '),
)

const medianX = computed(() =>
  x(props.scale === 'log' ? Math.log10(Math.max(props.median, 0.5)) : props.median),
)
/** Near the right edge the label flips to the left of its line. */
const medianAnchor = computed(() => (medianX.value > W - 150 ? 'end' : 'start'))

const hover = ref<number | null>(null)

function onMove(event: MouseEvent) {
  const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect()
  const px = ((event.clientX - rect.left) / rect.width) * W
  let best = 0
  let bestDistance = Infinity
  props.block.bins.forEach((bin, i) => {
    const distance = Math.abs(x((bin.x0 + bin.x1) / 2) - px)
    if (distance < bestDistance) {
      bestDistance = distance
      best = i
    }
  })
  hover.value = best
}

const hovered = computed(() => (hover.value === null ? null : props.block.bins[hover.value]))

function binRange(x0: number, x1: number): string {
  const toDays = (v: number) => (props.scale === 'log' ? Math.pow(10, v) : v)
  return `${labelDays(Math.max(Math.round(toDays(x0)), 0))} – ${labelDays(Math.round(toDays(x1)))}`
}
</script>

<template>
  <figure class="chart">
    <div class="frame">
      <svg
        :viewBox="`0 0 ${W} ${H}`"
        role="img"
        :aria-label="`在所天數分布，${scale === 'log' ? '對數' : '線性'}橫軸，中位數 ${median} 天`"
        @mousemove="onMove"
        @mouseleave="hover = null"
      >
        <line
          v-for="share in gridShares"
          :key="`g${share}`"
          class="gridline"
          :x1="PAD.left"
          :x2="W - PAD.right"
          :y1="y(yMax * share)"
          :y2="y(yMax * share)"
        />

        <rect
          v-for="(bar, index) in bars"
          :key="index"
          class="bar"
          :class="{ on: hover === index }"
          :x="bar.x"
          :y="bar.y"
          :width="bar.width"
          :height="bar.height"
        />
        <path class="kde" :d="linePath" />

        <line class="median" :x1="medianX" :x2="medianX" :y1="PAD.top" :y2="bottom" />
        <text
          class="median-label"
          :x="medianX + (medianAnchor === 'end' ? -6 : 6)"
          :y="PAD.top + 12"
          :text-anchor="medianAnchor"
        >
          中位數 {{ median.toLocaleString('zh-TW') }} 天
        </text>

        <g class="axis">
          <line :x1="PAD.left" :x2="W - PAD.right" :y1="bottom" :y2="bottom" />
          <template v-for="tick in ticks" :key="`t${tick.at}`">
            <line :x1="tick.at" :x2="tick.at" :y1="bottom" :y2="bottom + 4" />
            <text :x="tick.at" :y="bottom + 18" text-anchor="middle">{{ tick.label }}</text>
          </template>
          <text :x="PAD.left" :y="PAD.top - 4">密度</text>
        </g>
      </svg>
    </div>

    <figcaption v-if="hovered" class="readout">
      <strong>{{ binRange(hovered.x0, hovered.x1) }}</strong>
      <span>{{ hovered.count.toLocaleString('zh-TW') }} 隻</span>
    </figcaption>
    <figcaption v-else class="readout muted">滑過長條可讀出該區間的隻數。</figcaption>
  </figure>
</template>

<style scoped>
.chart {
  margin: 0;
}

/* Scrolls sideways on a phone rather than shrinking the tick labels past
   reading. */
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

.bar {
  fill: var(--ramp-2);

  &.on {
    fill: var(--ramp-4);
  }
}

.kde {
  fill: none;
  stroke: var(--ramp-5);
  stroke-width: 2;
  stroke-linejoin: round;
}

.median {
  stroke: var(--ink);
  stroke-width: 1.2;
  stroke-dasharray: 4 4;
}

.median-label {
  fill: var(--ink);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.axis line {
  stroke: var(--hairline);
}

.axis text {
  fill: var(--ink-muted);
  font-size: 11px;
}

.readout {
  display: flex;
  gap: 0.6rem;
  align-items: baseline;
  min-height: 1.4rem;
  margin-top: 0.4rem;
  color: var(--ink-secondary);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;

  &.muted {
    color: var(--ink-muted);
  }
}
</style>
