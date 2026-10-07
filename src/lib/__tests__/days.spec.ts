import { describe, expect, it } from 'vitest'
import { STALE_AFTER_DAYS, axisTicks, labelDays, snapshotAge, taipeiToday } from '@/lib/days'

/* Axis labels for the two charts on the analysis page.
 *
 * The unit switches twice as the number grows, and both switch points are
 * off-by-one territory. They are pinned because a wrong label on an axis is
 * the kind of error a reader trusts.
 */

describe('labelDays', () => {
  it('counts days below a month', () => {
    expect(labelDays(1)).toBe('1 天')
    expect(labelDays(29)).toBe('29 天')
  })

  it('switches to months at thirty days', () => {
    expect(labelDays(30)).toBe('1 個月')
    expect(labelDays(364)).toBe('12 個月')
  })

  it('switches to years at a year', () => {
    expect(labelDays(365)).toBe('1 年')
  })

  it('keeps one decimal for the first year and drops it after two', () => {
    // 1.1 年 is worth saying; 4.3 年 pretends to a precision the reader
    // cannot act on.
    expect(labelDays(400)).toBe('1.1 年')
    expect(labelDays(730)).toBe('2 年')
    expect(labelDays(1825)).toBe('5 年')
  })
})

describe('axisTicks', () => {
  it('uses whole years on the linear axis', () => {
    const ticks = axisTicks('linear', [])
    expect(ticks[0]).toEqual({ days: 0, label: '0' })
    expect(ticks.map((tick) => tick.label)).toContain('10 年')
  })

  it('names the log ticks the pipeline publishes', () => {
    const ticks = axisTicks('log', [7, 30, 365])
    expect(ticks.map((tick) => tick.label)).toEqual(['1 週', '1 個月', '1 年'])
  })

  it('falls back to a generated label for a tick with no name', () => {
    // distribution.json decides the log ticks; the component must not break
    // when the pipeline publishes one the label table has never seen.
    expect(axisTicks('log', [999])[0].label).toBe(labelDays(999))
  })

  it('keeps the order the pipeline published', () => {
    const ticks = axisTicks('log', [30, 7])
    expect(ticks.map((tick) => tick.days)).toEqual([30, 7])
  })
})

/* The footer's stale-snapshot notice. The day boundary is Taipei's, which is
 * eight hours ahead of UTC: the off-by-one this guards against is a reader
 * in Taipei after midnight, or a reader abroad, seeing the wrong age. */

describe('taipeiToday', () => {
  it('turns over at midnight Taipei time, not UTC', () => {
    expect(taipeiToday(new Date('2026-10-03T15:59:00Z'))).toBe('2026-10-03')
    expect(taipeiToday(new Date('2026-10-03T16:00:00Z'))).toBe('2026-10-04')
  })
})

describe('snapshotAge', () => {
  it('counts whole Taipei days since the snapshot', () => {
    // 2026-10-04 01:00 in Taipei.
    expect(snapshotAge('2026-10-01', new Date('2026-10-03T17:00:00Z'))).toBe(3)
  })

  it('reaches the warning threshold on the third day, not before', () => {
    const now = new Date('2026-10-04T02:00:00Z') // 10:00 in Taipei
    expect(snapshotAge('2026-10-02', now)).toBeLessThan(STALE_AFTER_DAYS)
    expect(snapshotAge('2026-10-01', now)).toBe(STALE_AFTER_DAYS)
  })

  it('has no age for an unreadable date', () => {
    expect(snapshotAge('', new Date())).toBeNull()
  })
})
