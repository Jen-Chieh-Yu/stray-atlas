<script setup lang="ts">
/** Cumulative share of animals against days in the shelter, 狗 versus 貓.
 *
 *  Paired with the KDE deliberately. The density's shape is an argument about
 *  the bandwidth; this curve has no bandwidth and no smoothing, so every figure
 *  quoted in the surrounding prose is read off here instead.
 */
import { computed, ref } from 'vue'

const props = defineProps<{
  series: { key: string; label: string; colour: string; points: [number, number][] }[]
  maxDays: number
  ticks: number[]
}>()

const W = 720
const H = 300
const PAD = { top: 16, right: 58, bottom: 34, left: 46 }
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom

function x(days: number): number {
  const lo = Math.log10(0.5)
  const hi = Math.log10(props.maxDays)
  return PAD.left + ((Math.log10(Math.max(days, 0.5)) - lo) / (hi - lo)) * plotW
}

function y(share: number): number {
  return PAD.top + plotH - share * plotH
}

/** Step, not line: the ECDF jumps at each observation and does not interpolate
 *  between two animals. Drawing it as a slope would claim values nobody had. */
const paths = computed(() =>
  props.series.map((s) => {
    let d = ''
    let previous = 0
    s.points.forEach((p, i) => {
      const px = x(p[0])
      if (i === 0) d += `M${px.toFixed(2)},${y(0).toFixed(2)}`
      else d += ` L${px.toFixed(2)},${y(previous).toFixed(2)}`
      d += ` L${px.toFixed(2)},${y(p[1]).toFixed(2)}`
      previous = p[1]
    })
    return { ...s, d, end: { x: x(s.points[s.points.length - 1][0]), y: y(1) } }
  }),
)

const gridShares = [0.25, 0.5, 0.75, 1]

function labelDays(days: number): string {
  if (days < 30) return `${days} 天`
  if (days < 365) return `${Math.round(days / 30)} 個月`
  return `${+(days / 365).toFixed(days >= 730 ? 0 : 1)} 年`
}

const cursor = ref<number | null>(null)

function onMove(event: MouseEvent) {
  const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect()
  const px = ((event.clientX - rect.left) / rect.width) * W
  cursor.value = Math.min(PAD.left + plotW, Math.max(PAD.left, px))
}

const cursorDays = computed(() => {
  if (cursor.value === null) return null
  const lo = Math.log10(0.5)
  const hi = Math.log10(props.maxDays)
  return Math.round(Math.pow(10, lo + ((cursor.value - PAD.left) / plotW) * (hi - lo)))
})

/** The share at or below the cursor, per series, by walking the thinned points. */
const readout = computed(() => {
  if (cursorDays.value === null) return []
  return props.series.map((s) => {
    let share = 0
    for (const [days, value] of s.points) {
      if (days > cursorDays.value!) break
      share = value
    }
    return { key: s.key, label: s.label, colour: s.colour, share }
  })
})
</script>

<template>
  <figure class="chart">
    <svg
      :viewBox="`0 0 ${W} ${H}`"
      role="img"
      aria-label="犬貓在所天數的累積分佈"
      @mousemove="onMove"
      @mouseleave="cursor = null"
    >
      <g class="grid">
        <line
          v-for="s in gridShares"
          :key="`h${s}`"
          :x1="PAD.left"
          :x2="PAD.left + plotW"
          :y1="y(s)"
          :y2="y(s)"
        />
        <line
          v-for="t in ticks.filter((d) => d <= maxDays)"
          :key="`v${t}`"
          :x1="x(t)"
          :x2="x(t)"
          :y1="PAD.top"
          :y2="PAD.top + plotH"
        />
      </g>

      <text v-for="s in gridShares" :key="`l${s}`" class="tick" :x="PAD.left - 6" :y="y(s) + 4" text-anchor="end">
        {{ Math.round(s * 100) }}%
      </text>

      <path
        v-for="p in paths"
        :key="p.key"
        class="line"
        :d="p.d"
        :style="{ stroke: p.colour }"
      />

      <!-- Anchored to where each curve actually reaches 100%, not stacked at
           the frame edge: the cat curve tops out years before the dog curve,
           and a label parked on the right would point at the wrong line. -->
      <text
        v-for="p in paths"
        :key="`e${p.key}`"
        class="direct-label"
        :x="p.end.x + 6"
        :y="y(1) - 6"
        :style="{ fill: p.colour }"
      >
        {{ p.label }}
      </text>

      <line
        class="axis"
        :x1="PAD.left"
        :x2="PAD.left + plotW"
        :y1="PAD.top + plotH"
        :y2="PAD.top + plotH"
      />
      <text
        v-for="t in ticks.filter((d) => d <= maxDays)"
        :key="`t${t}`"
        class="tick"
        :x="x(t)"
        :y="PAD.top + plotH + 16"
        text-anchor="middle"
      >
        {{ labelDays(t) }}
      </text>
      <text class="axis-title" :x="PAD.left" :y="H - 4">已在所天數（對數）</text>

      <template v-if="cursor !== null">
        <line class="cursor" :x1="cursor" :x2="cursor" :y1="PAD.top" :y2="PAD.top + plotH" />
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

    <figcaption v-if="cursorDays !== null" class="readout">
      <strong>{{ labelDays(cursorDays) }}以內</strong>
      <span v-for="r in readout" :key="r.key">
        <i class="swatch" :style="{ background: r.colour }" aria-hidden="true" />
        {{ r.label }} {{ (r.share * 100).toFixed(1) }}%
      </span>
    </figcaption>
    <figcaption v-else class="readout muted">
      滑過任一位置可讀出該天數以內的累積比例。
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

.line {
  fill: none;
  stroke-width: 2;
  stroke-linejoin: round;
}

.axis {
  stroke: var(--ink-muted);
  stroke-width: 1;
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

.direct-label {
  font-size: 12px;
  font-weight: 600;
}

.readout {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  align-items: baseline;
  margin-top: 0.4rem;
  min-height: 1.4rem;
  font-size: 0.8rem;
  color: var(--ink-secondary);
}

.readout.muted {
  color: var(--ink-muted);
}

.swatch {
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 2px;
  margin-right: 0.3rem;
}
</style>
