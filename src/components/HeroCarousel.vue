<script setup lang="ts">
/** The photo band behind the home page title: illustrative photos that
 *  cross-fade every few seconds.
 *
 *  The credit line names the photographer of the photo on screen and says the
 *  animals are not in a shelter, so no slide can be read as a listing.
 *  Autoplay stops while the pointer or keyboard focus is inside, while the
 *  tab is hidden, and never starts for visitors who ask for reduced motion;
 *  the pause button stops it for good.
 *
 *  Used by: HomeView.vue.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { HERO_PHOTOS } from '@/lib/heroPhotos'

const INTERVAL_MS = 6000

const index = ref(0)
const playing = ref(true)
const hovered = ref(false)
const focused = ref(false)
const hidden = ref(false)

const current = computed(() => HERO_PHOTOS[index.value])

/** Only the slides seen so far and the next one are in the DOM, so a visit
 *  that never waits for the carousel downloads two photos, not eight. */
const loaded = ref(new Set<number>([0, 1 % HERO_PHOTOS.length]))
watch(index, (value) => {
  const next = new Set(loaded.value)
  next.add(value)
  next.add((value + 1) % HERO_PHOTOS.length)
  loaded.value = next
})

function go(to: number) {
  index.value = (to + HERO_PHOTOS.length) % HERO_PHOTOS.length
}

const running = computed(() => playing.value && !hovered.value && !focused.value && !hidden.value)

let timer: number | undefined
watch(
  running,
  (on) => {
    window.clearInterval(timer)
    timer = on ? window.setInterval(() => go(index.value + 1), INTERVAL_MS) : undefined
  },
)

function onVisibility() {
  hidden.value = document.visibilityState === 'hidden'
}

function onFocusOut(event: FocusEvent) {
  const root = event.currentTarget as HTMLElement
  focused.value = root.contains(event.relatedTarget as Node | null)
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) playing.value = false
  document.addEventListener('visibilitychange', onVisibility)
  if (running.value) timer = window.setInterval(() => go(index.value + 1), INTERVAL_MS)
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
  <div
    class="carousel"
    role="region"
    aria-roledescription="carousel"
    aria-label="示意照片"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
    @focusin="focused = true"
    @focusout="onFocusOut"
  >
    <template v-for="(photo, i) in HERO_PHOTOS" :key="photo.id">
      <img
        v-if="loaded.has(i)"
        :class="{ on: i === index }"
        :src="photo.small"
        :srcset="`${photo.small} 960w, ${photo.large} 1920w`"
        sizes="100vw"
        :alt="i === index ? photo.alt : ''"
        :aria-hidden="i === index ? undefined : 'true'"
        :style="{ objectPosition: photo.focus }"
        :fetchpriority="i === 0 ? 'high' : undefined"
        decoding="async"
      />
    </template>

    <p class="credit" aria-live="polite">
      示意照片，非收容所動物 · Photo by
      <a :href="current.url" target="_blank" rel="noreferrer">{{ current.photographer }}</a>
      / Unsplash
    </p>

    <div class="controls">
      <button
        type="button"
        class="toggle"
        :aria-label="playing ? '暫停輪播' : '播放輪播'"
        @click="playing = !playing"
      >
        <LucideIcon :name="playing ? 'pause' : 'play'" :size="14" />
      </button>
      <button
        v-for="(photo, i) in HERO_PHOTOS"
        :key="photo.id"
        type="button"
        class="dot"
        :aria-label="`第 ${i + 1} 張，共 ${HERO_PHOTOS.length} 張`"
        :aria-current="i === index ? 'true' : undefined"
        @click="go(i)"
      />
    </div>
  </div>
</template>

<style scoped>
.carousel {
  position: relative;
  overflow: hidden;
  aspect-ratio: 2.25 / 1;
  /* Keep the search box within reach of the first screen. */
  max-height: min(600px, 62vh);
  width: 100%;
  background: var(--surface-sunk);

  & img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    transition: opacity 900ms ease;

    &.on {
      opacity: 1;
    }
  }
}

/* Credit bottom-left, controls bottom-right: the title plate overlaps the
   bottom centre, so both sit in the corners it leaves free. */
.credit,
.controls {
  position: absolute;
  bottom: 0.9rem;
  z-index: 1;
  margin: 0;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ink) 55%, transparent);
  color: var(--on-accent);
}

.credit {
  left: 1rem;
  padding: 0.25rem 0.7rem;
  font-size: 0.74rem;

  & a {
    color: inherit;
  }
}

.controls {
  right: 1rem;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.25rem 0.6rem 0.25rem 0.3rem;
}

.toggle {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: inherit;
  cursor: pointer;

  &:hover {
    background: color-mix(in srgb, var(--on-accent) 18%, transparent);
  }
}

.dot {
  width: 8px;
  height: 8px;
  padding: 0;
  border: 1px solid var(--on-accent);
  border-radius: 999px;
  background: transparent;
  cursor: pointer;

  &[aria-current='true'] {
    background: var(--on-accent);
  }
}

.toggle:focus-visible,
.dot:focus-visible,
.credit a:focus-visible {
  outline: 2px solid var(--on-accent);
  outline-offset: 2px;
}

/* Between the plate's width and the phone layout the corners are too
   narrow for the plate to overlap, so the chrome moves to the top. */
@media (max-width: 1000px) {
  .credit,
  .controls {
    top: 0.8rem;
    bottom: auto;
  }
}

/* Phones: a squarer crop keeps more of each photo; the plate sits below. */
@media (max-width: 700px) {
  .carousel {
    aspect-ratio: 4 / 3;
  }

  .credit,
  .controls {
    top: auto;
    bottom: 0.7rem;
  }

  .credit {
    left: 0.7rem;
    max-width: calc(100% - 10.5rem);
  }

  .controls {
    right: 0.7rem;
    gap: 0.35rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .carousel img {
    transition: none;
  }
}
</style>
