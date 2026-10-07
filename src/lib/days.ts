import type { Scale } from '@/types'

/* Day labels and axis ticks shared by the two charts on the analysis page,
 *  the snapshot's age for the footer, and days in the shelter.
 *
 *  Used by: DistributionChart.vue and EcdfChart.vue (labels and ticks),
 *  App.vue (snapshotAge, STALE_AFTER_DAYS), and useAtlasData.ts, which
 *  passes daysInShelter on to the pages, and vite.config.ts, which writes it
 *  into the share pages.
 */

/** Days in the shelter, measured against the snapshot rather than today. */
export function daysInShelter(created: string, snapshotDate: string): number | null {
  const from = Date.parse(created)
  const to = Date.parse(snapshotDate)
  if (Number.isNaN(from) || Number.isNaN(to)) return null
  return Math.round((to - from) / 86400000)
}

/** The footer warns from this many days. The schedule stores a snapshot a
 *  day, finishing between about 09:45 and 14:40 Taipei time, and the source
 *  skips the odd day, so one or two days behind is normal. */
export const STALE_AFTER_DAYS = 3

/** Today in Taipei as YYYY-MM-DD: snapshots are named by Taipei days, so a
 *  reader abroad must not see a different age for the same snapshot. */
export function taipeiToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Taipei' }).format(now)
}

/** Whole days from the snapshot to today in Taipei; null when unreadable. */
export function snapshotAge(snapshotDate: string, now: Date = new Date()): number | null {
  const from = Date.parse(snapshotDate)
  const to = Date.parse(taipeiToday(now))
  if (Number.isNaN(from) || Number.isNaN(to)) return null
  return Math.round((to - from) / 86400000)
}

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
