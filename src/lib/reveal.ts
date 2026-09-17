import type { Directive } from 'vue'

/** v-reveal: fade a block in the first time it scrolls into view.
 *
 *  Only blocks that start below the fold are hidden, and only once the
 *  observer is in place, so nothing the visitor can already see ever blinks
 *  out, and a browser without IntersectionObserver (or a visitor who asks
 *  for reduced motion) simply sees the page as it is. Each block reveals
 *  once; scrolling back up does not replay it. The styles are .reveal and
 *  .is-visible in style.css.
 *
 *  An optional value tunes one element:
 *    appear  fade in even if it is already on screen, for items the visitor
 *            has just asked for (the shelter list's 查看更多)
 *    delay   milliseconds to wait, to stagger a batch of such items
 *
 *  Used by: HomeView.vue, AnimalsView.vue, ShelterListView.vue,
 *  AnalysisView.vue and AboutView.vue. Import it as vReveal in
 *  <script setup>. */

export interface RevealOptions {
  appear?: boolean
  delay?: number
}

let observer: IntersectionObserver | null = null

function watcher(): IntersectionObserver {
  observer ??= new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        entry.target.classList.add('is-visible')
        observer?.unobserve(entry.target)
      }
    },
    // Start a little before the block's top edge reaches the bottom of the
    // screen, so the fade is under way by the time it is read.
    { rootMargin: '0px 0px -8% 0px', threshold: 0.08 },
  )
  return observer
}

function motionAllowed(): boolean {
  return (
    typeof IntersectionObserver !== 'undefined' &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

export const vReveal: Directive<HTMLElement, RevealOptions | undefined> = {
  mounted(el, binding) {
    if (!motionAllowed()) return
    const options = binding.value ?? {}
    if (!options.appear) {
      const box = el.getBoundingClientRect()
      if (box.top < window.innerHeight && box.bottom > 0) return
    }
    if (options.delay) el.style.setProperty('--reveal-delay', `${options.delay}ms`)
    el.classList.add('reveal')
    // The observer reports an element already on screen on its next frame,
    // after the hidden state has been styled, so the fade still plays.
    watcher().observe(el)
  },
  unmounted(el) {
    observer?.unobserve(el)
  },
}
