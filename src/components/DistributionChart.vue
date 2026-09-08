<script setup lang="ts">
/** Histogram with a KDE curve over it, on a switchable log10 / linear axis.
 *
 *  Bars and curve share one y axis because both are densities: the bars carry
 *  count / (n × bin width), the curve integrates to 1 over the same axis. A
 *  count axis would put them on different scales and the overlay would be a
 *  decoration rather than a comparison.
 */
import { computed, ref } from 'vue'
import type { ScaleBlock, Scale, Smoothing } from '@/types'

const props = defineProps<{
  block: ScaleBlock
  scale: Scale
  smoothing: Smoothing
  logTicks: number[]
  maxDays: number
  median: number
  colour: string
}>()

const W = 720
const H = 300
const PAD = { top: 16, right: 16, bottom: 34, left: 46 }
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom

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
  return Math.max(bars, line) * 1.08
})

function x(value: number): number {
  const [lo, hi] = domain.value
  return PAD.left + ((value - lo) / (hi - lo)) * plotW
}

function y(value: number): number {
  return PAD.top + plotH - (value / yMax.value) * plotH
}

/** Axis position for a value in days, whichever scale is showing. */
function xDays(days: number): number {
  return x(props.scale === 'log' ? Math.log10(Math.max(days, 0.5)) : days)
}

const ticks = computed(() => {
  if (props.scale === 'log') {
    return props.logTicks
      .filter((d) => d <= props.maxDays)
      .map((d) => ({ at: xDays(d), label: labelDays(d) }))
  }
  const step = props.maxDays > 3000 ? 1000 : 500
  const out = []
  for (let d = 0; d <= props.maxDays; d += step) out.push({ at: xDays(d), label: `${d}` })
  return out
})

function labelDays(days: number): string {
  if (days < 30) return `${days} 天`
  if (days < 365) return `${Math.round(days / 30)} 個月`
  return `${+(days / 365).toFixed(days >= 730 ? 0 : 1)} 年`
}

const barPath = computed(() =>
  props.block.bins
    .map((b) => {
      const x0 = x(b.x0)
      const x1 = x(b.x1)
      // 2px of surface between fills, per the mark spec; skip it if the bin is
      // narrower than the gap would be.
      const inset = x1 - x0 > 4 ? 1 : 0
      return `M${(x0 + inset).toFixed(2)},${y(0).toFixed(2)} L${(x0 + inset).toFixed(2)},${y(b.density).toFixed(2)} L${(x1 - inset).toFixed(2)},${y(b.density).toFixed(2)} L${(x1 - inset).toFixed(2)},${y(0).toFixed(2)} Z`
    })
    .join(' '),
)

const linePath = computed(() =>
  curve.value.points
    .map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(2)},${y(p[1]).toFixed(2)}`)
    .join(' '),
)

const hover = ref<{ i: number; cx: number } | null>(null)

function onMove(event: MouseEvent) {
  const target = event.currentTarget as SVGSVGElement
  const rect = target.getBoundingClientRect()
  const px = ((event.clientX - rect.left) / rect.width) * W
  let best = 0
  let bestDistance = Infinity
  props.block.bins.forEach((b, i) => {
    const centre = x((b.x0 + b.x1) / 2)
    const distance = Math.abs(centre - px)
    if (distance < bestDistance) {
      bestDistance = distance
      best = i
    }
  })
  const bin = props.block.bins[best]
  hover.value = { i: best, cx: x((bin.x0 + bin.x1) / 2) }
}

const hovered = computed(() => (hover.value ? props.block.bins[hover.value.i] : null))

function binRange(x0: number, x1: number): string {
  const toDays = (v: number) => (props.scale === 'log' ? Math.pow(10, v) : v)
  return `${labelDays(Math.max(Math.round(toDays(x0)), 0))} – ${labelDays(Math.round(toDays(x1)))}`
}
</script>

<template>
  <figure class="chart">
    <svg
      :viewBox="`0 0 ${W} ${H}`"
      role="img"
      :aria-label="`在所天數分佈，${scale === 'log' ? '對數' : '線性'}橫軸`"
      @mousemove="onMove"
      @mouseleave="hover = null"
    >
      <g class="grid">
        <line
          v-for="t in ticks"
          :key="`g${t.at}`"
          :x1="t.at"
          :x2="t.at"
          :y1="PAD.top"
          :y2="PAD.top + plotH"
        />
      </g>

      <path class="bars" :d="barPath" />
      <path class="kde" :d="linePath" :style="{ stroke: colour }" />

      <line
        class="median"
        :x1="xDays(median)"
        :x2="xDays(median)"
        :y1="PAD.top"
        :y2="PAD.top + plotH"
      />
      <text class="median-label" :x="xDays(median) + 5" :y="PAD.top + 11">
        中位數 {{ median.toLocaleString('zh-TW') }} 天
      </text>

      <line
        class="axis"
        :x1="PAD.left"
        :x2="PAD.left + plotW"
        :y1="PAD.top + plotH"
        :y2="PAD.top + plotH"
      />
      <text
        v-for="t in ticks"
        :key="`t${t.at}`"
        class="tick"
        :x="t.at"
        :y="PAD.top + plotH + 16"
        text-anchor="middle"
      >
        {{ t.label }}
      </text>
      <text class="axis-title" :x="PAD.left" :y="H - 4">已在所天數</text>
      <text class="axis-title" :x="PAD.left" :y="PAD.top - 4">機率密度</text>

      <template v-if="hover && hovered">
        <line
          class="cursor"
          :x1="hover.cx"
          :x2="hover.cx"
          :y1="PAD.top"
          :y2="PAD.top + plotH"
        />
        <circle :cx="hover.cx" :cy="y(hovered.density)" r="4.5" :style="{ fill: colour }" />
      </template>
    </svg>

    <figcaption v-if="hovered" class="readout">
      <strong>{{ binRange(hovered.x0, hovered.x1) }}</strong>
      <span>{{ hovered.count.toLocaleString('zh-TW') }} 隻</span>
    </figcaption>
    <figcaption v-else class="readout muted">
      滑過長條可讀出該區間的隻數。曲線為核密度估計，頻寬 {{ curve.bandwidth }}
      <template v-if="scale === 'log'">（log₁₀ 天）</template>
      <template v-else>天</template>
    </figcaption>
  </figure>
</template>

<style scoped>
.chart {
  margin: 0;
}

svg {
  display: block;
  width: 100%;
  height: auto;
}

.grid line {
  stroke: var(--hairline);
  stroke-width: 1;
}

.bars {
  fill: var(--surface-sunk);
  stroke: var(--hairline);
  stroke-width: 1;
}

.kde {
  fill: none;
  stroke-width: 2;
  stroke-linejoin: round;
}

.axis {
  stroke: var(--ink-muted);
  stroke-width: 1;
}

.median {
  stroke: var(--ink-secondary);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.median-label {
  fill: var(--ink-secondary);
  font-size: 11px;
}

.cursor {
  stroke: var(--ink-muted);
  stroke-width: 1;
}

.tick,
.axis-title {
  fill: var(--ink-muted);
  font-size: 11px;
}

.readout {
  display: flex;
  gap: 0.6rem;
  align-items: baseline;
  margin-top: 0.4rem;
  min-height: 1.4rem;
  font-size: 0.8rem;
  color: var(--ink-secondary);
}

.readout.muted {
  color: var(--ink-muted);
}
</style>
