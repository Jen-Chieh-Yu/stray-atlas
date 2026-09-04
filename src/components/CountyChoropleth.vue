<script setup lang="ts">
import { computed, ref } from 'vue'
import { geoMercator, geoPath } from 'd3-geo'
import type { GeoPermissibleObjects } from 'd3-geo'
import type { CountyCollection, CountyFeature } from '@/types'

const props = defineProps<{
  shapes: CountyCollection
  values: Map<string, number | null>
  breaks: number[]
  selected: string | null
  /** Raw counts, used only for the inset labels — an inset a few pixels across
   *  carries its number as text instead. */
  counts?: Map<string, number>
}>()

const emit = defineEmits<{ hover: [string | null]; select: [string | null] }>()

const WIDTH = 560
const HEIGHT = 588  // the height the framed bbox actually needs at this width

/** 金門 sits 180 km west of Taiwan and 連江 100 km north of that. Fitting one
 *  projection to all of them shrinks the main island to a third of the frame
 *  and fills the rest with empty sea, so both are drawn as insets — the
 *  convention on every printed map of Taiwan. */
const INSETS: { counties: string[]; label: string; box: [[number, number], [number, number]] }[] =
  [
    { counties: ['連江縣'], label: '連江', box: [[14, 120], [118, 224]] },
    { counties: ['金門縣'], label: '金門', box: [[14, 240], [118, 344]] },
    { counties: ['澎湖縣'], label: '澎湖', box: [[14, 360], [118, 464]] },
  ]
const INSET_COUNTIES = new Set(INSETS.flatMap((inset) => inset.counties))

const hovered = ref<string | null>(null)

/** The main view is framed on an explicit bounding box, not on the data.
 *
 * 高雄市 administratively includes 東沙群島 and 南沙太平島, the latter at
 * 10.4°N — fitting the projection to the data's own extent therefore reaches
 * into the South China Sea and shrinks Taiwan to a thumbnail. Those two
 * islands fall outside the frame and are clipped; the caveat text says so.
 */
const MAIN_VIEW: [[number, number], [number, number]] = [
  [119.9, 21.75],
  [122.1, 25.4],
]

function ringArea(ring: number[][]): number {
  let total = 0
  for (let i = 0; i < ring.length - 1; i += 1) {
    total += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
  }
  return Math.abs(total / 2)
}

/** Frame an inset on its main islands, ignoring the distant specks.
 *
 * 金門縣 also administers 烏坵, 130 km north-east, and 連江縣 spreads over
 * 50 km; framing on the full extent leaves the inset showing sea. Islands
 * under a twentieth of the largest one are left outside the frame, which is
 * what a printed map does too.
 */
function mainIslandsFrame(features: CountyFeature[]): [[number, number], [number, number]] {
  const rings = features.flatMap((feature) => feature.geometry.coordinates.map((poly) => poly[0]))
  const largest = Math.max(...rings.map(ringArea))
  const kept = rings.filter((ring) => ringArea(ring) >= largest / 20)
  const xs = kept.flatMap((ring) => ring.map((point) => point[0]))
  const ys = kept.flatMap((ring) => ring.map((point) => point[1]))
  return [
    [Math.min(...xs), Math.min(...ys)],
    [Math.max(...xs), Math.max(...ys)],
  ]
}

function boxOf(bounds: [[number, number], [number, number]]) {
  const [[west, south], [east, north]] = bounds
  return {
    type: 'Polygon',
    coordinates: [
      // Clockwise, matching the ring order d3-geo treats as interior. Wound
      // the other way this box is "everything except Taiwan" and fitExtent
      // scales the whole planet into the frame.
      [
        [west, south],
        [west, north],
        [east, north],
        [east, south],
        [west, south],
      ],
    ],
  } as unknown as GeoPermissibleObjects
}

function project(
  features: CountyFeature[],
  extent: [[number, number], [number, number]],
  frame?: [[number, number], [number, number]],
) {
  const fitTo = frame
    ? boxOf(frame)
    : ({ type: 'FeatureCollection', features } as unknown as GeoPermissibleObjects)
  const render = geoPath(geoMercator().fitExtent(extent, fitTo))
  return features.map((feature) => ({
    county: feature.properties.county,
    d: render(feature as unknown as GeoPermissibleObjects) ?? '',
  }))
}

const mainPaths = computed(() =>
  project(
    props.shapes.features.filter((f) => !INSET_COUNTIES.has(f.properties.county)),
    [
      [140, 10],
      [WIDTH - 10, HEIGHT - 10],
    ],
    MAIN_VIEW,
  ),
)

const insetPaths = computed(() =>
  INSETS.map((inset) => {
    const features = props.shapes.features.filter((f) =>
      inset.counties.includes(f.properties.county),
    )
    return {
      label: inset.label,
      box: inset.box,
      counties: inset.counties,
      paths: project(
        features,
        [
          [inset.box[0][0] + 8, inset.box[0][1] + 8],
          [inset.box[1][0] - 8, inset.box[1][1] - 20],
        ],
        mainIslandsFrame(features),
      ),
    }
  }),
)

/** Sequential ramp: one hue, light to dark, six classes from the parent's
 *  break points, so the scale is stated in the legend rather than implied. */
function fillFor(county: string): string {
  const value = props.values.get(county)
  if (value === null || value === undefined) return 'var(--no-data)'
  let step = 1
  for (const cut of props.breaks) {
    if (value > cut) step += 1
  }
  return `var(--ramp-${Math.min(step, 6)})`
}

function isDimmed(county: string): boolean {
  const active = props.selected ?? hovered.value
  return active !== null && active !== county
}

function enter(county: string) {
  hovered.value = county
  emit('hover', county)
}

function leave() {
  hovered.value = null
  emit('hover', null)
}

function toggle(county: string) {
  emit('select', props.selected === county ? null : county)
}
</script>

<template>
  <svg
    class="map"
    :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
    role="img"
    aria-label="臺灣各縣市在所動物分布圖"
    @mouseleave="leave"
  >
    <g v-for="inset in insetPaths" :key="inset.label">
      <rect
        class="inset-frame"
        :x="inset.box[0][0]"
        :y="inset.box[0][1]"
        :width="inset.box[1][0] - inset.box[0][0]"
        :height="inset.box[1][1] - inset.box[0][1]"
        rx="8"
      />
      <text class="inset-label" :x="inset.box[0][0] + 8" :y="inset.box[1][1] - 8">
        {{ inset.label }}
      </text>
      <text
        v-if="counts"
        class="inset-count"
        :x="inset.box[1][0] - 8"
        :y="inset.box[1][1] - 8"
        text-anchor="end"
      >
        {{ (counts.get(inset.counties[0]) ?? 0).toLocaleString('zh-TW') }} 隻
      </text>
      <path
        v-for="shape in inset.paths"
        :key="shape.county"
        :d="shape.d"
        :fill="fillFor(shape.county)"
        :class="{
          county: true,
          inset: true,
          dimmed: isDimmed(shape.county),
          active: selected === shape.county,
        }"
        tabindex="0"
        role="button"
        :aria-label="shape.county"
        @mouseenter="enter(shape.county)"
        @focus="enter(shape.county)"
        @blur="leave"
        @click="toggle(shape.county)"
        @keydown.enter.prevent="toggle(shape.county)"
      />
    </g>

    <path
      v-for="shape in mainPaths"
      :key="shape.county"
      :d="shape.d"
      :fill="fillFor(shape.county)"
      :class="{ county: true, dimmed: isDimmed(shape.county), active: selected === shape.county }"
      tabindex="0"
      role="button"
      :aria-label="shape.county"
      @mouseenter="enter(shape.county)"
      @focus="enter(shape.county)"
      @blur="leave"
      @click="toggle(shape.county)"
      @keydown.enter.prevent="toggle(shape.county)"
    />
  </svg>
</template>

<style scoped>
.map {
  width: 100%;
  height: auto;
  display: block;
}

.county {
  /* A surface-coloured gap between fills: adjacent counties in neighbouring
     classes would otherwise read as one shape. */
  stroke: var(--surface);
  stroke-width: 1.4;
  stroke-linejoin: round;
  cursor: pointer;
  transition:
    opacity 120ms ease,
    stroke 120ms ease;
  outline: none;
}

.county.dimmed {
  opacity: 0.3;
}

.county.active,
.county:focus-visible {
  stroke: var(--ink);
  stroke-width: 2;
}

.county.inset {
  /* The Matsu and Kinmen islands are a few pixels across; the full-width
     surface stroke would erase them. */
  stroke-width: 0.5;
}

.inset-frame {
  fill: none;
  stroke: var(--hairline);
  stroke-width: 1;
}

.inset-label,
.inset-count {
  fill: var(--ink-muted);
  font-size: 12px;
  font-family: var(--font);
}

.inset-count {
  font-variant-numeric: tabular-nums;
}
</style>
