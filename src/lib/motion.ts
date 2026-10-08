import { ref } from 'vue'
import { ICONS } from '@/lib/icons'

/* Motion for the shortlist (DESIGN.md §15): the animal's photo thrown into
 * the top bar when it is added, and rows that fade and fold away when
 * removed. A visitor who asks for reduced motion gets the end state at once.
 *
 * Used by: AnimalCard.vue and AnimalDialog.vue (the throw), App.vue (the
 * count that waits for it) and ShortlistView.vue (folding rows). */

export function motionAllowed(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof Element.prototype.animate === 'function' &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/** Calls `then` once the animation ends, or is cancelled, or `ms` have
 *  passed, whichever comes first, and only once. A hidden tab stops the
 *  animation clock, and nothing (a count, a row's removal) may wait on it. */
function settle(animation: Animation, ms: number, then: () => void) {
  let settled = false
  const finish = () => {
    if (settled) return
    settled = true
    window.clearTimeout(late)
    then()
  }
  const late = window.setTimeout(finish, ms + 400)
  animation.onfinish = finish
  animation.oncancel = finish
}

/** Ends a hook without animating, but not synchronously: a <Transition> in
 *  out-in mode breaks when its leave finishes inside the leave call. */
function skip(done: () => void) {
  window.setTimeout(done, 0)
}

export interface Point {
  x: number
  y: number
}

/** Points along a throw from `from` to `to`, evenly spaced in time: a
 *  quadratic curve with its control point midway across and above both
 *  ends, which moves at a steady pace sideways and rises then falls, as a
 *  thrown thing does. The control point comes down just far enough to keep
 *  every point `top` pixels below the top of the screen, and never below
 *  the higher end, where the curve goes flat. */
export function arc(from: Point, to: Point, steps = 24, top = 28): Point[] {
  const cx = (from.x + to.x) / 2
  const floor = Math.min(from.y, to.y)
  const weights = Array.from({ length: steps + 1 }, (_, i) => {
    const t = i / steps
    return [(1 - t) ** 2, 2 * (1 - t) * t, t ** 2] as const
  })
  // Each point's height is linear in the control point's, so the lowest
  // control point that keeps each one on screen can be solved for directly.
  let cy = floor - Math.min(220, Math.max(60, Math.abs(to.x - from.x) * 0.35))
  for (const [a, b, c] of weights) {
    if (b > 0) cy = Math.max(cy, (top - a * from.y - c * to.y) / b)
  }
  cy = Math.min(cy, floor)
  return weights.map(([a, b, c]) => ({
    x: a * from.x + b * cx + c * to.x,
    y: a * from.y + b * cy + c * to.y,
  }))
}

/* ── The throw ─────────────────────────────────────────────────────────────
 * The top bar marks where to land with data-shortlist-target: the 候選清單
 * link on a wide screen, the menu button on a phone. Whichever is showing
 * is the target. */

/** Photos still in the air. The top bar shows the count less these, so its
 *  number goes up as each photo lands rather than when the button is hit. */
export const inFlight = ref(0)

const FLIGHT_MS = 650
const LANDED_PX = 20

function target(): HTMLElement | null {
  for (const element of document.querySelectorAll<HTMLElement>('[data-shortlist-target]')) {
    const box = element.getBoundingClientRect()
    if (box.width > 0 && box.height > 0) return element
  }
  return null
}

function bookmark(size: number): SVGSVGElement {
  const ns = 'http://www.w3.org/2000/svg'
  const svg = document.createElementNS(ns, 'svg')
  svg.setAttribute('viewBox', '0 0 24 24')
  svg.setAttribute('width', String(size))
  svg.setAttribute('height', String(size))
  svg.setAttribute('fill', 'none')
  svg.setAttribute('stroke', 'currentColor')
  svg.setAttribute('stroke-width', '2')
  for (const shape of ICONS.bookmark) {
    const path = document.createElementNS(ns, 'path')
    path.setAttribute('d', shape.d)
    svg.append(path)
  }
  return svg
}

/** Throws a round copy of `from` (the photo, or a bookmark when there is
 *  none) into the top bar, shrinking as it goes, and bumps the target when
 *  it lands. The copy sits above the dialog's backdrop and takes no clicks. */
export function flyToShortlist(from: Element, photo: string | null) {
  if (!motionAllowed() || document.hidden) return
  const landing = target()
  if (!landing) return
  const start = from.getBoundingClientRect()
  const size = Math.min(160, start.width, start.height)
  if (size <= 0) return
  const end = landing.getBoundingClientRect()
  const origin = { x: start.left + start.width / 2, y: start.top + start.height / 2 }
  const points = arc(origin, { x: end.left + end.width / 2, y: end.top + end.height / 2 })

  const token = document.createElement('div')
  token.className = 'shortlist-fly'
  token.setAttribute('aria-hidden', 'true')
  Object.assign(token.style, {
    left: `${origin.x - size / 2}px`,
    top: `${origin.y - size / 2}px`,
    width: `${size}px`,
    height: `${size}px`,
  })
  if (photo) {
    const img = document.createElement('img')
    img.src = photo
    img.alt = ''
    img.referrerPolicy = 'no-referrer'
    token.append(img)
  } else {
    token.append(bookmark(Math.round(size * 0.45)))
  }
  document.body.append(token)
  inFlight.value += 1

  const last = points.length - 1
  const flight = token.animate(
    points.map((point, i) => {
      const t = i / last
      const scale = 1 + (LANDED_PX / size - 1) * t
      return {
        transform: `translate(${point.x - origin.x}px, ${point.y - origin.y}px) scale(${scale})`,
        opacity: t < 0.9 ? 1 : 1 - (t - 0.9) * 5,
      }
    }),
    { duration: FLIGHT_MS, easing: 'linear', fill: 'forwards' },
  )

  settle(flight, FLIGHT_MS, () => {
    token.remove()
    inFlight.value -= 1
    landing.animate(
      [{ transform: 'scale(1)' }, { transform: 'scale(1.18)' }, { transform: 'scale(1)' }],
      { duration: 250, easing: 'ease-out' },
    )
  })
}

/* ── Folding rows ──────────────────────────────────────────────────────────
 * Hooks for <Transition> and <TransitionGroup :css="false">. A row fades
 * out, then folds its height away so the rows below close the gap; one put
 * back opens up first, then fades in. */

const FOLD_MS = 400

function folded(): Keyframe {
  return {
    height: '0px',
    paddingTop: '0px',
    paddingBottom: '0px',
    marginTop: '0px',
    marginBottom: '0px',
    borderTopWidth: '0px',
    borderBottomWidth: '0px',
    opacity: 0,
    overflow: 'hidden',
    boxSizing: 'border-box',
  }
}

function open(element: HTMLElement, opacity: number): Keyframe {
  const style = getComputedStyle(element)
  return {
    height: `${element.offsetHeight}px`,
    paddingTop: style.paddingTop,
    paddingBottom: style.paddingBottom,
    marginTop: style.marginTop,
    marginBottom: style.marginBottom,
    borderTopWidth: style.borderTopWidth,
    borderBottomWidth: style.borderBottomWidth,
    opacity,
    overflow: 'hidden',
    boxSizing: 'border-box',
  }
}

export function foldAway(element: Element, done: () => void) {
  if (!motionAllowed()) return skip(done)
  const node = element as HTMLElement
  const shown = open(node, 1)
  const faded = { ...shown, opacity: 0, offset: 0.5 }
  const fold = node.animate([shown, faded, folded()], {
    duration: FOLD_MS,
    easing: 'ease-in-out',
    fill: 'forwards',
  })
  settle(fold, FOLD_MS, done)
}

export function unfold(element: Element, done: () => void) {
  if (!motionAllowed()) return skip(done)
  const node = element as HTMLElement
  const shown = open(node, 1)
  const opened = { ...shown, opacity: 0, offset: 0.5 }
  const grow = node.animate([folded(), opened, shown], {
    duration: FOLD_MS,
    easing: 'ease-in-out',
  })
  settle(grow, FOLD_MS, done)
}

/** For swapping the whole list and the empty state. */
export function fadeOut(element: Element, done: () => void) {
  if (!motionAllowed()) return skip(done)
  const fade = (element as HTMLElement).animate([{ opacity: 1 }, { opacity: 0 }], {
    duration: 200,
    easing: 'ease-in',
    fill: 'forwards',
  })
  settle(fade, 200, done)
}

export function fadeIn(element: Element, done: () => void) {
  if (!motionAllowed()) return skip(done)
  const fade = (element as HTMLElement).animate([{ opacity: 0 }, { opacity: 1 }], {
    duration: 200,
    easing: 'ease-out',
  })
  settle(fade, 200, done)
}
