import type { Scale } from '@/types'

/* Day labels and axis ticks shared by the two charts on the analysis page.
 *
 *  Used by: DistributionChart.vue and EcdfChart.vue.
 */

/** Names for the log ticks the pipeline publishes (distribution.json). */
const LOG_LABELS: Record<number, string> = {
  1: '1 天',
  7: '1 週',
  30: '1 個月',
  90: '3 個月',
  365: '1 年',
  730: '2 年',
  1825: '5 年',
  3650: '10 年',
}

/** Whole years on the linear axis, so its ticks read in the same units as the
 *  log axis. */
const LINEAR_TICKS: [number, string][] = [
  [0, '0'],
  [365, '1 年'],
  [730, '2 年'],
  [1460, '4 年'],
  [2190, '6 年'],
  [2920, '8 年'],
  [3650, '10 年'],
  [4380, '12 年'],
]

export function axisTicks(scale: Scale, logTicks: number[]): { days: number; label: string }[] {
  if (scale === 'linear') return LINEAR_TICKS.map(([days, label]) => ({ days, label }))
  return logTicks.map((days) => ({ days, label: LOG_LABELS[days] ?? labelDays(days) }))
}

/** A day count in the unit a reader would say it in. */
export function labelDays(days: number): string {
  if (days < 30) return `${days} 天`
  if (days < 365) return `${Math.round(days / 30)} 個月`
  return `${+(days / 365).toFixed(days >= 730 ? 0 : 1)} 年`
}
