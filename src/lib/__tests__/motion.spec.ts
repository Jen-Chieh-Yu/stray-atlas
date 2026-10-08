import { describe, expect, it } from 'vitest'
import { arc } from '@/lib/motion'

// A card photo at 1280px and the top bar's 候選清單 pill above and to its right.
const card = { x: 180, y: 520 }
const pill = { x: 1180, y: 30 }

describe('arc', () => {
  it('starts on the photo and lands on the target', () => {
    const points = arc(card, pill)
    expect(points).toHaveLength(25)
    expect(points[0]).toEqual(card)
    expect(points[24].x).toBeCloseTo(pill.x)
    expect(points[24].y).toBeCloseTo(pill.y)
  })

  it('moves sideways at a steady pace, as a throw does', () => {
    const steps = arc(card, pill)
      .slice(1)
      .map((point, i, rest) => point.x - (i === 0 ? card.x : rest[i - 1].x))
    for (const step of steps) expect(step).toBeCloseTo(steps[0])
  })

  it('rises above both ends when there is room', () => {
    const highest = Math.min(...arc({ x: 90, y: 400 }, { x: 330, y: 300 }).map((point) => point.y))
    expect(highest).toBeLessThan(300)
  })

  it('keeps 28px below the top of the screen when the target is near it', () => {
    const points = arc(card, pill)
    expect(Math.min(...points.slice(0, -1).map((point) => point.y))).toBeGreaterThanOrEqual(28)
  })
})
