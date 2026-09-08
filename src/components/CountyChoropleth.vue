<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { geoMercator, geoPath } from 'd3-geo'
import type { GeoPermissibleObjects, GeoProjection } from 'd3-geo'
import type { CountyCollection, CountyFeature, ShelterPoint } from '@/types'

const props = defineProps<{
  shapes: CountyCollection
  values: Map<string, number | null>
  breaks: number[]
  selected: string | null
  /** Raw counts, used only for the inset labels — an inset a few pixels across
   *  carries its number as text instead. */
  counts?: Map<string, number>
  /** Shelter markers. Absent or empty draws the choropleth alone. */
  points?: ShelterPoint[]
  showPoints?: boolean
}>()

const emit = defineEmits<{
  hover: [string | null]
  select: [string | null]
  openShelter: [string]
  zoom: [number]
}>()

const WIDTH = 560
const HEIGHT = 588  // the height the framed bbox actually needs at this width

/** 金門 sits 180 km west of Taiwan and 連江 100 km north of that. Fitting one
 *  projection to all of them shrinks the main island to a third of the frame
 *  and fills the rest with empty sea, so both are drawn as insets — the
 *  convention on every printed map of Taiwan. */
const INSETS: { counties: string[]; label: string; box: [[number, number], [number, number]] }[] =
  [
    { counties: ['連江縣'], label: '連江', box: [[10, 10], [104, 104]] },
    { counties: ['金門縣'], label: '金門', box: [[10, 112], [104, 206]] },
    { counties: ['澎湖縣'], label: '澎湖', box: [[10, 214], [104, 308]] },
  ]
const INSET_COUNTIES = new Set(INSETS.flatMap((inset) => inset.counties))

/* The insets own a strip down the left edge, and the main map is clipped out
 * of it.
 *
 * At 1x nothing overlaps: the main projection is fitted from x=140 and the
 * insets end at 104. Zooming breaks that — the island grows leftwards and runs
 * underneath the inset plates, so 連江 and 金門 end up sitting on top of 新北
 * and 桃園. Reserving the strip is what a printed map does: the inset is not
 * over the map, it is beside it.
 */
const GUTTER = 112
const CLIP_ID = 'county-map-viewport'

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

function projectionFor(
  features: CountyFeature[],
  extent: [[number, number], [number, number]],
  frame?: [[number, number], [number, number]],
): GeoProjection {
  const fitTo = frame
    ? boxOf(frame)
    : ({ type: 'FeatureCollection', features } as unknown as GeoPermissibleObjects)
  return geoMercator().fitExtent(extent, fitTo)
}

function draw(features: CountyFeature[], projection: GeoProjection) {
  const render = geoPath(projection)
  return features.map((feature) => ({
    county: feature.properties.county,
    d: render(feature as unknown as GeoPermissibleObjects) ?? '',
  }))
}

const mainFeatures = computed(() =>
  props.shapes.features.filter((f) => !INSET_COUNTIES.has(f.properties.county)),
)

const mainProjection = computed(() =>
  projectionFor(
    mainFeatures.value,
    [
      [140, 10],
      [WIDTH - 10, HEIGHT - 10],
    ],
    MAIN_VIEW,
  ),
)

const mainPaths = computed(() => draw(mainFeatures.value, mainProjection.value))

const insetPaths = computed(() =>
  INSETS.map((inset) => {
    const features = props.shapes.features.filter((f) =>
      inset.counties.includes(f.properties.county),
    )
    const projection = projectionFor(
      features,
      [
        // Extra room at the top: a pin hangs about 23px above its own tip, and
        // an island framed tight against the ceiling has its marker clipped.
        [inset.box[0][0] + 8, inset.box[0][1] + 26],
        [inset.box[1][0] - 12, inset.box[1][1] - 20],
      ],
      mainIslandsFrame(features),
    )
    return {
      label: inset.label,
      box: inset.box,
      counties: inset.counties,
      paths: draw(features, projection),
      // 連江縣 keeps both its shelters in 南竿鄉, so their district centroids
      // are the same point and one pin would sit exactly on the other. Inside
      // a 94px box there is no room to lay them out properly; a few pixels
      // apart at least shows that there are two.
      pins: (() => {
        const placed = (props.points ?? [])
          .filter((p) => inset.counties.includes(p.county))
          .map((p) => {
            const at = projection([p.lon, p.lat])
            return { ...p, x: at?.[0] ?? 0, y: at?.[1] ?? 0 }
          })
        const groups = new Map<string, typeof placed>()
        for (const pin of placed) {
          const key = `${pin.x.toFixed(1)},${pin.y.toFixed(1)}`
          groups.set(key, [...(groups.get(key) ?? []), pin])
        }
        for (const group of groups.values()) {
          if (group.length < 2) continue
          group.forEach((pin, index) => {
            const angle = (index / group.length) * Math.PI * 2
            pin.x += Math.cos(angle) * 11
            pin.y += Math.sin(angle) * 7
          })
        }
        return placed
      })(),
    }
  }),
)

/* ------------------------------------------------------------------ zoom --
 * One transform on the map group, and markers drawn outside it.
 *
 * Scaling the whole SVG would scale the pins with it: at 6x a pin becomes a
 * banner covering three counties. So the geography lives in a scaled <g> and
 * every pin is positioned by applying the same transform by hand, which keeps
 * pins one size at every zoom level — the behaviour of every map that has
 * markers on it.
 */
const MAX_SCALE = 12
const view = ref({ k: 1, x: 0, y: 0 })
const dragging = ref(false)
const svgElement = ref<SVGSVGElement | null>(null)

function clampView(next: { k: number; x: number; y: number }) {
  const k = Math.min(MAX_SCALE, Math.max(1, next.k))
  // Never let the frame pan off the map: at k the content is k×WIDTH wide, so
  // the translate has to stay between (1 − k)·WIDTH and 0.
  const x = Math.min(0, Math.max((1 - k) * WIDTH, next.x))
  const y = Math.min(0, Math.max((1 - k) * HEIGHT, next.y))
  return { k, x, y }
}

function setView(next: { k: number; x: number; y: number }) {
  view.value = clampView(next)
  emit('zoom', view.value.k)
}

function at(point: [number, number] | null): { x: number; y: number } {
  if (!point) return { x: -99, y: -99 }
  return { x: point[0] * view.value.k + view.value.x, y: point[1] * view.value.k + view.value.y }
}

/** Client pixels to viewBox units. The SVG scales to its container, so a
 *  wheel event's offset means nothing until it is divided by that ratio. */
function toViewBox(event: MouseEvent | WheelEvent): [number, number] {
  const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect()
  return [
    ((event.clientX - rect.left) / rect.width) * WIDTH,
    ((event.clientY - rect.top) / rect.height) * HEIGHT,
  ]
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  const [px, py] = toViewBox(event)
  const factor = Math.exp(-event.deltaY * 0.0015)
  const k = Math.min(MAX_SCALE, Math.max(1, view.value.k * factor))
  // Keep whatever is under the pointer under the pointer.
  setView({
    k,
    x: px - ((px - view.value.x) / view.value.k) * k,
    y: py - ((py - view.value.y) / view.value.k) * k,
  })
}

let dragFrom: { x: number; y: number; vx: number; vy: number } | null = null
let dragMoved = false

/* Panning is tracked with listeners on the window, not with
 * setPointerCapture.
 *
 * Capture is the tidier API right up to the moment a press does not get its
 * pointerup back — the pointer leaves the window, the tab loses focus, a
 * native drag starts. The capture then never lifts, and because a captured
 * pointer bypasses hit testing entirely, EVERY later click on the page goes to
 * the map: the panel beside it stops responding and nothing on screen explains
 * why. Window listeners removed on release cannot strand anything.
 */
function endDrag() {
  dragFrom = null
  dragging.value = false
  window.removeEventListener('pointermove', onWindowMove)
  window.removeEventListener('pointerup', endDrag)
  window.removeEventListener('pointercancel', endDrag)
  window.removeEventListener('blur', endDrag)
}

function onWindowMove(event: PointerEvent) {
  if (!dragFrom || !svgElement.value) return
  const rect = svgElement.value.getBoundingClientRect()
  const ratio = WIDTH / rect.width
  const dx = (event.clientX - dragFrom.x) * ratio
  const dy = (event.clientY - dragFrom.y) * ratio
  if (Math.abs(dx) + Math.abs(dy) > 3) dragMoved = true
  setView({ k: view.value.k, x: dragFrom.vx + dx, y: dragFrom.vy + dy })
}

function onPointerDown(event: PointerEvent) {
  // Cleared on every press, not only on the ones that can pan. Left set from a
  // previous gesture it survives a zoom back out to 1x, and from then on every
  // click is swallowed as the tail of a drag that ended long ago.
  dragMoved = false
  if (view.value.k <= 1 || event.button !== 0) return
  dragFrom = { x: event.clientX, y: event.clientY, vx: view.value.x, vy: view.value.y }
  dragging.value = true
  window.addEventListener('pointermove', onWindowMove)
  window.addEventListener('pointerup', endDrag)
  window.addEventListener('pointercancel', endDrag)
  window.addEventListener('blur', endDrag)
}

onBeforeUnmount(endDrag)

/** Frame one county. Worked out in projected pixels rather than by refitting
 *  the projection, so the geometry is computed once and the camera is the only
 *  thing that moves. */
function focusCounty(county: string | null) {
  if (!county || INSET_COUNTIES.has(county)) {
    setView({ k: 1, x: 0, y: 0 })
    return
  }
  const feature = mainFeatures.value.find((f) => f.properties.county === county)
  if (!feature) return
  const [[x0, y0], [x1, y1]] = geoPath(mainProjection.value).bounds(
    feature as unknown as GeoPermissibleObjects,
  )
  const k = Math.min(MAX_SCALE, (0.8 * Math.min(WIDTH / (x1 - x0), HEIGHT / (y1 - y0))) || 1)
  setView({
    k,
    x: WIDTH / 2 - ((x0 + x1) / 2) * k,
    y: HEIGHT / 2 - ((y0 + y1) / 2) * k,
  })
}

/** Selecting no longer moves the camera.
 *
 * It used to: clicking a county framed it. But once framed, the neighbouring
 * counties are outside the viewport, so the reader who wanted to look at the
 * county next door had no way to click it — the first click locked them in.
 * Framing is now double-click, which nobody does by accident, and a single
 * click only opens the panel.
 */
function frameCounty(county: string) {
  focusCounty(county)
}

function zoomBy(factor: number) {
  const k = Math.min(MAX_SCALE, Math.max(1, view.value.k * factor))
  setView({
    k,
    x: WIDTH / 2 - ((WIDTH / 2 - view.value.x) / view.value.k) * k,
    y: HEIGHT / 2 - ((HEIGHT / 2 - view.value.y) / view.value.k) * k,
  })
}

function resetView() {
  setView({ k: 1, x: 0, y: 0 })
}

defineExpose({ resetView })

/* ---------------------------------------------------------------- marks -- */

const maxCount = computed(() => Math.max(1, ...(props.points ?? []).map((p) => p.count)))

/** Radius by the square root of the count, so area carries the number. Sizing
 *  by radius is the classic bubble-map error: it squares the difference. */
function radiusFor(count: number): number {
  return 9 + 8 * Math.sqrt(count / maxCount.value)
}

function pinPath(r: number): string {
  const tail = r * 1.55
  return `M0,0 C${-r * 0.62},${-tail * 0.52} ${-r},${-tail * 0.78} ${-r},${-tail} A${r},${r} 0 1,1 ${r},${-tail} C${r},${-tail * 0.78} ${-(-r) * 0.62},${-tail * 0.52} 0,0 Z`
}

/* Pins are one ink, not a second sequential ramp.
 *
 * Two reasons. The choropleth beneath already spends the ramp on magnitude,
 * and a second scale in the same hue reads as the same scale. And the ramp
 * inverts between themes — light-on-dark — so a pin coloured by count would
 * carry white numerals on a pale fill in dark mode. Ink against surface is
 * legible in both, and the count is already carried by the size and printed
 * inside the pin.
 */

const mainPins = computed(() => {
  if (!props.showPoints) return []
  return (props.points ?? [])
    .filter((p) => !INSET_COUNTIES.has(p.county))
    .map((p) => ({ ...p, base: mainProjection.value([p.lon, p.lat]) as [number, number] | null }))
    // Painter's order: southern pins drawn last so an overlap hides the pin
    // behind rather than a random one.
    .sort((a, b) => (a.base?.[1] ?? 0) - (b.base?.[1] ?? 0))
})

/** Names once the camera is close, and then only for the pins that fit.
 *
 *  Nine shelters share 新北市 and several sit two kilometres apart, so a label
 *  on every pin overlaps at any zoom that shows them all. Labels are laid out
 *  largest-count first and one is dropped as soon as its box would touch a box
 *  already placed — the reader loses a name rather than reading two names
 *  printed over each other.
 */
const labelled = computed(() => {
  const keep = new Set<string>()
  if (view.value.k < 2.5) return keep
  // Seeded with the pins themselves: a label is no more readable printed over
  // a neighbouring pin than over a neighbouring label.
  const placed: [number, number, number, number][] = mainPins.value.map((pin) => {
    const { x, y } = at(pin.base)
    const r = radiusFor(pin.count)
    return [x - r, y - r * 2.55, x + r, y] as [number, number, number, number]
  })
  for (const pin of [...mainPins.value].sort((a, b) => b.count - a.count)) {
    const { x, y } = at(pin.base)
    const half = Math.max(28, pin.name.replace(pin.county, '').length * 4.6)
    const box: [number, number, number, number] = [x - half, y + 6, x + half, y + 18]
    if (placed.some((b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1])) continue
    placed.push(box)
    keep.add(pin.id)
  }
  return keep
})

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

/** Always reports the county that was clicked; it never decides that a second
 *  click means "close".
 *
 *  It used to, by comparing against props.selected. But selected is also set
 *  when a pin is clicked - a shelter belongs to a county - so with a shelter
 *  card open, clicking that shelter's own county read as a repeat click and
 *  collapsed the panel instead of opening the county. Only the parent knows
 *  what the panel is currently showing, so only the parent can tell a repeat
 *  from a switch. */
function toggle(county: string) {
  // A pan that ended on a county must not also select it.
  if (dragMoved) return
  emit('select', county)
}

function openShelter(id: string) {
  if (dragMoved) return
  emit('openShelter', id)
}
</script>

<template>
  <div class="wrap">
    <svg
      ref="svgElement"
      class="map"
      :class="{ dragging, pannable: view.k > 1 }"
      :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
      role="img"
      aria-label="臺灣各縣市在所動物分布圖"
      @mouseleave="leave"
      @wheel="onWheel"
      @pointerdown="onPointerDown"
    >
      <defs>
        <clipPath :id="CLIP_ID">
          <rect :x="GUTTER" y="0" :width="WIDTH - GUTTER" :height="HEIGHT" />
        </clipPath>
      </defs>
      <!-- Two groups, not one. clip-path resolves in the user space that the
           element's own transform establishes, so a clip and a transform on
           the same <g> means the clip rectangle is scaled and panned with the
           map — at 8x it lands somewhere off in the sea. The outer group
           carries the clip in untransformed viewBox units; the inner one
           carries the camera. -->
      <g :clip-path="`url(#${CLIP_ID})`">
        <g :transform="`translate(${view.x},${view.y}) scale(${view.k})`">
        <path
          v-for="shape in mainPaths"
          :key="shape.county"
          :d="shape.d"
          :fill="fillFor(shape.county)"
          :class="{
            county: true,
            muted: showPoints,
            dimmed: isDimmed(shape.county),
            active: selected === shape.county,
          }"
          vector-effect="non-scaling-stroke"
          tabindex="0"
          role="button"
          :aria-label="shape.county"
          @mouseenter="enter(shape.county)"
          @focus="enter(shape.county)"
          @blur="leave"
          @click="toggle(shape.county)"
          @dblclick.prevent="frameCounty(shape.county)"
          @keydown.enter.prevent="toggle(shape.county)"
          />
        </g>
      </g>

      <!-- Outside the scaled group on purpose: see the zoom note above. -->
      <g v-if="showPoints" class="pins" :clip-path="`url(#${CLIP_ID})`">
        <g
          v-for="pin in mainPins"
          :key="pin.id"
          class="pin"
          :transform="`translate(${at(pin.base).x},${at(pin.base).y})`"
          tabindex="0"
          role="button"
          :aria-label="`${pin.name}，${pin.count} 隻，中位數 ${pin.median_days ?? '—'} 天`"
          @click.stop="openShelter(pin.id)"
          @keydown.enter.prevent="openShelter(pin.id)"
        >
          <path :d="pinPath(radiusFor(pin.count))" />
          <text
            :y="-radiusFor(pin.count) * 1.55"
            dy="4"
            :font-size="Math.min(12, radiusFor(pin.count) * 0.8)"
          >
            {{ pin.count }}
          </text>
          <text v-if="labelled.has(pin.id)" class="pin-name" y="13">
            {{ pin.name.replace(pin.county, '') }}
          </text>
          <title>{{ pin.name }}・{{ pin.count }} 隻・中位數 {{ pin.median_days ?? '—' }} 天</title>
        </g>
      </g>
      <line
        v-if="view.k > 1.01"
        class="gutter-edge"
        :x1="GUTTER"
        :x2="GUTTER"
        y1="0"
        :y2="HEIGHT"
      />

      <!-- Drawn last and on an opaque plate. These three counties have no
           place in the main frame, so they must stay legible at every zoom
           level; painted underneath they would be covered by the zoomed main
           island, and painted transparently they would show it through. -->
      <g v-for="inset in insetPaths" :key="inset.label" class="inset-group">
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
            muted: showPoints,
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
        <g
          v-for="pin in inset.pins"
          v-show="showPoints"
          :key="pin.id"
          class="pin small"
          :transform="`translate(${pin.x},${pin.y})`"
          tabindex="0"
          role="button"
          :aria-label="`${pin.name}，${pin.count} 隻`"
          @click.stop="openShelter(pin.id)"
          @keydown.enter.prevent="openShelter(pin.id)"
        >
          <path :d="pinPath(10)" />
          <text y="-15.5" dy="3.4" :font-size="pin.count >= 100 ? 8 : 9.5">
            {{ pin.count }}
          </text>
          <title>{{ pin.name }}・{{ pin.count }} 隻</title>
        </g>
      </g>
    </svg>

    <!-- Bottom right, where a map's zoom control lives. Both buttons work
         about the frame's centre, so pressing − repeatedly lands back on the
         whole country: that is the way out, and it needs no separate reset. -->
    <div class="zoom-controls">
      <button
        type="button"
        class="zoom-button"
        aria-label="放大"
        @click="zoomBy(1.6)"
      >
        ＋
      </button>
      <button
        type="button"
        class="zoom-button"
        aria-label="縮小"
        :disabled="view.k <= 1"
        @click="zoomBy(1 / 1.6)"
      >
        －
      </button>
    </div>
  </div>
</template>

<style scoped>
.wrap {
  position: relative;
}

.map {
  width: 100%;
  height: auto;
  display: block;
  touch-action: none;
}

.map.pannable {
  cursor: grab;
}

.map.dragging {
  cursor: grabbing;
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

/* With pins on, the choropleth is context rather than the subject: at full
   strength the two sequential scales compete and neither reads. */
.county.muted {
  opacity: 0.45;
}

.county.dimmed {
  opacity: 0.3;
}

.county.muted.dimmed {
  opacity: 0.18;
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

.gutter-edge {
  stroke: var(--hairline);
  stroke-width: 1;
}

.inset-frame {
  fill: var(--surface);
  stroke: var(--hairline);
  stroke-width: 1;
}

.inset-label,
.inset-count {
  font-size: 11px;
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

.pin {
  cursor: pointer;
  outline: none;
}

.pin path {
  fill: var(--ink);
  stroke: var(--surface);
  stroke-width: 1.5;
}

.pin text {
  fill: var(--surface);
  text-anchor: middle;
  font-family: var(--font);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
}

.pin .pin-name {
  fill: var(--ink-secondary);
  font-size: 9px;
  font-weight: 500;
}

.pin:hover path,
.pin:focus-visible path {
  stroke: var(--ink);
  stroke-width: 2;
}

.zoom-controls {
  position: absolute;
  right: 10px;
  bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zoom-button {
  font: inherit;
  font-size: 0.9rem;
  line-height: 1;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--hairline);
  background: var(--surface);
  color: var(--ink-secondary);
  cursor: pointer;
}

.zoom-button:disabled {
  opacity: 0.4;
  cursor: default;
}

.zoom-button:hover:not(:disabled) {
  border-color: var(--ramp-3);
}
</style>
