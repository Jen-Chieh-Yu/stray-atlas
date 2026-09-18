<script setup lang="ts">
/** Rows on a shared logarithmic day axis: a span, one or two dots on it.
 *
 *  Used by AnalysisView.vue for both of the comparison blocks (DESIGN.md
 *  §11). One component rather than two because the two blocks are the same
 *  picture with different meanings attached — a group's quartile range with
 *  its median, and a shelter's two medians with the gap between them. Sharing
 *  it is what keeps the axis, the tick positions and the row rhythm identical
 *  between the two, which is the whole reason they can be read one after the
 *  other.
 *
 *  Positions are percentages of the log range, computed here and written as
 *  inline `left`/`width`. No SVG: the rows are text with a strip of colour in
 *  them, so they reflow, wrap and print like text. The axis and the grid
 *  lines are drawn per row so they line up with that row's track exactly,
 *  whatever the label column is doing at this width.
 *
 *  Days are never zero here (an animal recorded today is 0 days in, and
 *  log10(0) is not a number), so values are clamped to the axis minimum and
 *  the axis starts above zero. A clamped value sits on the left edge rather
 *  than disappearing, and the caller states the axis bounds on the page.
 */
import { computed } from 'vue'

export interface SpanTick {
  days: number
  label: string
}

export interface SpanDot {
  days: number
  /** solid: the one figure of the row. open/dark: the pair being compared. */
  variant?: 'solid' | 'open' | 'dark'
  /** Read out by screen readers in place of the bare number. */
  title?: string
}

export interface SpanRow {
  key: string
  label: string
  /** Second line under the label: sample sizes, a county name. */
  sub?: string
  /** Short word after the label, for a row the reader should discount. */
  flag?: string
  start: number
  end: number
  /** How the span itself reads. 'range' is a quartile range; 'up' and 'down'
   *  are a gap with a direction, and the caller says in its legend which
   *  direction is which. */
  tone?: 'range' | 'up' | 'down'
  dots: SpanDot[]
  /** Right-hand figure, already formatted — this component does no rounding
   *  and no unit-guessing. */
  figure: string
  /** Quieter figure to the right of it: a sample size, a unit. */
  aside?: string
}

const props = withDefaults(
  defineProps<{
    minDays: number
    maxDays: number
    ticks: SpanTick[]
    groups: { title?: string; rows: SpanRow[] }[]
    /** An extra rule across every track, such as the overall median. */
    marker?: { days: number; label: string } | null
    /** Wider label column for the rows whose labels are shelter names. */
    wide?: boolean
    caption: string
  }>(),
  { marker: null, wide: false },
)

const span = computed(() => Math.log10(props.maxDays) - Math.log10(props.minDays))

function position(days: number): number {
  const clamped = Math.min(Math.max(days, props.minDays), props.maxDays)
  return ((Math.log10(clamped) - Math.log10(props.minDays)) / span.value) * 100
}

function left(days: number): string {
  return `${position(days).toFixed(3)}%`
}

function width(from: number, to: number): string {
  return `${Math.max(position(to) - position(from), 0).toFixed(3)}%`
}
</script>

<template>
  <div class="spanchart" :class="{ wide }" role="img" :aria-label="caption">
    <div class="axis">
      <span v-for="tick in ticks" :key="tick.days" :style="{ left: left(tick.days) }">
        {{ tick.label }}
      </span>
      <span v-if="marker" class="markerlab" :style="{ left: left(marker.days) }">
        {{ marker.label }}
      </span>
    </div>

    <div v-for="(group, index) in groups" :key="group.title ?? index" class="sgroup">
      <h3 v-if="group.title">{{ group.title }}</h3>
      <div v-for="row in group.rows" :key="row.key" class="srow">
        <span class="lab">
          {{ row.label }}<em v-if="row.flag" class="flag">{{ row.flag }}</em>
          <em v-if="row.sub">{{ row.sub }}</em>
        </span>
        <span class="track">
          <i
            v-for="tick in ticks"
            :key="tick.days"
            class="gl"
            :style="{ left: left(tick.days) }"
          ></i>
          <i v-if="marker" class="gl mark" :style="{ left: left(marker.days) }"></i>
          <i
            class="span"
            :class="row.tone ?? 'range'"
            :style="{ left: left(row.start), width: width(row.start, row.end) }"
          ></i>
          <i
            v-for="(dot, dotIndex) in row.dots"
            :key="dotIndex"
            class="dot"
            :class="dot.variant ?? 'solid'"
            :style="{ left: left(dot.days) }"
            :title="dot.title"
          ></i>
        </span>
        <b class="fig">{{ row.figure }}</b>
        <span class="aside">{{ row.aside ?? '' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The label and figure columns are fixed so that the tracks — and therefore
   every grid line and dot — share one coordinate space down the whole chart.
   The axis reserves the same gutters. */
.spanchart {
  --lab: 9rem;
  --fig: 4rem;
  --aside: 3rem;

  &.wide {
    --lab: 12rem;
    --fig: 4.4rem;
    --aside: 2rem;
  }
}

.axis {
  position: relative;
  height: 1.4rem;
  margin-left: var(--lab);
  margin-right: calc(var(--fig) + var(--aside));
  color: var(--ink-muted);
  font-size: 0.74rem;

  & span {
    position: absolute;
    transform: translateX(-50%);
    white-space: nowrap;
  }

  & .markerlab {
    color: var(--accent-text);
  }
}

.sgroup + .sgroup {
  margin-top: 1.3rem;
}

.sgroup h3 {
  margin-bottom: 0.35rem;
  color: var(--ink-muted);
  font-size: 0.84rem;
  font-weight: 500;
}

.srow {
  display: grid;
  grid-template-columns: var(--lab) 1fr var(--fig) var(--aside);
  align-items: center;
  padding: 0.28rem 0;

  & + .srow {
    border-top: 1px solid var(--hairline);
  }
}

.lab {
  padding-right: 0.8rem;
  font-size: 0.88rem;
  line-height: 1.3;

  & em {
    display: block;
    color: var(--ink-muted);
    font-size: 0.7rem;
    font-style: normal;
    font-variant-numeric: tabular-nums;
  }

  & .flag {
    display: inline;
    margin-left: 0.4rem;
  }
}

.track {
  position: relative;
  height: 22px;
}

.gl {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--hairline);

  /* The shared reference line. Darker than a grid line, lighter than ink, so
     it reads as a rule rather than as data. */
  &.mark {
    background: var(--ink);
    opacity: 0.28;
  }
}

.span {
  position: absolute;
  top: 50%;
  height: 3px;
  margin-top: -1.5px;
  border-radius: 2px;
  background: var(--ramp-1);

  &.up {
    background: var(--ramp-3);
  }

  /* The minority direction is drawn quieter, not in a second hue: this
     project has one accent ramp and two categorical slots already spoken
     for by 狗 and 貓 (DESIGN.md §3). */
  &.down {
    background: var(--ink-muted);
    opacity: 0.45;
  }
}

.dot {
  position: absolute;
  top: 50%;
  width: 9px;
  height: 9px;
  margin: -4.5px 0 0 -4.5px;
  border-radius: 50%;
  background: var(--ramp-4);

  &.open {
    background: var(--surface);
    border: 2px solid var(--ramp-2);
  }

  &.dark {
    background: var(--ramp-5);
  }
}

.fig {
  padding-left: 0.6rem;
  font-size: 0.88rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.aside {
  padding-left: 0.5rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

@media (max-width: 820px) {
  .spanchart,
  .spanchart.wide {
    --lab: 7rem;
    --fig: 3.4rem;
    --aside: 2.4rem;
  }
}
</style>
