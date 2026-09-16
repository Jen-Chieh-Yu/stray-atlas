<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import LucideIcon from '@/components/LucideIcon.vue'

interface NavItem {
  to: string
  label: string
  /** Route names that count as this section, so /shelters/:id still marks 收容所. */
  names: string[]
}

const NAV: NavItem[] = [
  { to: '/animals', label: '找動物', names: ['animals'] },
  { to: '/shelters', label: '收容所', names: ['shelters', 'shelter'] },
  { to: '/map', label: '縣市地圖', names: ['map'] },
  { to: '/analysis', label: '資料分析', names: ['analysis'] },
  { to: '/about', label: '關於本站', names: ['about'] },
]

/** Must match the breakpoint below where the inline nav gives way to the menu button. */
const NARROW_QUERY = '(max-width: 820px)'

const route = useRoute()

function isCurrent(item: NavItem): boolean {
  return typeof route.name === 'string' && item.names.includes(route.name)
}

const navOpen = ref(false)
const toggleButton = ref<HTMLButtonElement | null>(null)
const closeButton = ref<HTMLButtonElement | null>(null)

/** Focus follows the panel so keyboard users are never left behind a covered page.
 *  `restoreFocus` is false when a route change closes the panel: the new page is
 *  where attention belongs, not the menu button. */
async function setNavOpen(open: boolean, restoreFocus = true) {
  if (navOpen.value === open) return
  navOpen.value = open
  document.body.style.overflow = open ? 'hidden' : ''
  // The panel is visibility: hidden until the class lands, and a hidden
  // element refuses focus, so wait for the render first.
  await nextTick()
  if (open) closeButton.value?.focus()
  else if (restoreFocus) toggleButton.value?.focus()
}

watch(
  () => route.fullPath,
  () => void setNavOpen(false, false),
)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && navOpen.value) void setNavOpen(false)
}

// Widening past the breakpoint hides the button; a panel left open there would
// cover the page with no visible way to close it.
let narrow: MediaQueryList | null = null
function onBreakpointChange(event: MediaQueryListEvent) {
  if (!event.matches) void setNavOpen(false, false)
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  narrow = window.matchMedia(NARROW_QUERY)
  narrow.addEventListener('change', onBreakpointChange)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  narrow?.removeEventListener('change', onBreakpointChange)
  document.body.style.overflow = ''
})
</script>

<template>
  <header class="topbar">
    <div class="wrap topbar-inner">
      <RouterLink to="/" class="wordmark">StrayAtlas 浪浪地圖</RouterLink>

      <nav class="mainnav" aria-label="主要導覽">
        <RouterLink
          v-for="item in NAV"
          :key="item.to"
          :to="item.to"
          :class="{ current: isCurrent(item) }"
          :aria-current="isCurrent(item) ? 'page' : undefined"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <button
        ref="toggleButton"
        type="button"
        class="nav-toggle"
        aria-label="開啟選單"
        aria-controls="navpanel"
        :aria-expanded="navOpen"
        @click="setNavOpen(true)"
      >
        <LucideIcon name="menu" :size="22" />
      </button>
    </div>

    <nav id="navpanel" class="navpanel" :class="{ open: navOpen }" aria-label="主要導覽（選單）">
      <div class="wrap navpanel-head">
        <RouterLink to="/" class="wordmark">StrayAtlas 浪浪地圖</RouterLink>
        <button
          ref="closeButton"
          type="button"
          class="nav-close"
          aria-label="關閉選單"
          @click="setNavOpen(false)"
        >
          <LucideIcon name="x" :size="24" />
        </button>
      </div>

      <div class="wrap navpanel-links">
        <RouterLink
          v-for="item in NAV"
          :key="item.to"
          :to="item.to"
          :class="{ current: isCurrent(item) }"
          :aria-current="isCurrent(item) ? 'page' : undefined"
        >
          {{ item.label }}
          <LucideIcon name="chevron-right" :size="18" />
        </RouterLink>
      </div>
    </nav>
  </header>

  <main :class="route.meta.fullBleed ? 'bleed' : 'wrap main'">
    <RouterView />
  </main>

  <footer class="footer">
    <div class="wrap footer-inner">
      <p>
        資料來源：農業部「動物認領養」開放資料（<a
          href="https://data.gov.tw/dataset/85903"
          rel="noreferrer"
          target="_blank"
          >dataset 85903</a
        >），依政府資料開放授權條款第 1 版使用。行政區界線為內政部「鄉鎮市區界線」（dataset 7441）。動物照片由
        <a href="https://www.pet.gov.tw/" rel="noreferrer" target="_blank">pet.gov.tw</a> 提供。
      </p>
      <p>
        本專案程式碼目前保留所有權利，尚未選定開放授權條款。介面圖示採用
        <a href="https://lucide.dev" rel="noreferrer" target="_blank">Lucide</a>（ISC License）。
      </p>
    </div>
  </footer>
</template>

<style scoped>
/* ── Top bar ── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  background: var(--surface);
  border-bottom: 1px solid var(--hairline);
}

.topbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  height: 60px;
}

.wordmark {
  font-weight: 700;
  font-size: 1.05rem;
  white-space: nowrap;
  color: inherit;
  text-decoration: none;
}

.wordmark:hover {
  color: var(--accent-text);
}

.mainnav {
  display: flex;
  align-items: center;
  gap: 1.4rem;
}

.mainnav a {
  color: var(--ink-secondary);
  text-decoration: none;
  font-size: 0.92rem;
}

.mainnav a:hover {
  color: var(--ink);
}

.mainnav a.current {
  color: var(--ink);
  font-weight: 700;
}

/* ── Menu button and full-screen panel (≤ 820px) ── */
.nav-toggle,
.nav-close {
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin-right: -0.5rem;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
  cursor: pointer;
}

.nav-toggle {
  display: none;
}

.nav-close {
  display: flex;
}

.nav-toggle:hover,
.nav-close:hover {
  background: var(--surface-sunk);
}

/* Slides in from the right and covers the page. visibility (not display) keeps
   the transition, and also takes the closed panel's links out of the tab order. */
.navpanel {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  background: var(--plane);
  transform: translateX(100%);
  visibility: hidden;
  transition:
    transform 300ms cubic-bezier(0.4, 0, 0.2, 1),
    visibility 0s linear 300ms;
}

.navpanel.open {
  transform: translateX(0);
  visibility: visible;
  transition:
    transform 300ms cubic-bezier(0.4, 0, 0.2, 1),
    visibility 0s;
}

/* In a column flex container, .wrap's auto margins stop the child stretching. */
.navpanel > .wrap {
  width: 100%;
}

.navpanel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  height: 60px;
  flex-shrink: 0;
  background: var(--surface);
  border-bottom: 1px solid var(--hairline);
}

.navpanel-links {
  flex: 1;
  overflow-y: auto;
  padding-top: 0.5rem;
}

.navpanel-links a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.05rem 0;
  font-size: 1.1rem;
  color: var(--ink);
  text-decoration: none;
  border-bottom: 1px solid var(--hairline);
}

.navpanel-links a:last-child {
  border-bottom: 0;
}

.navpanel-links a svg {
  color: var(--ink-muted);
}

.navpanel-links a.current {
  color: var(--accent-text);
  font-weight: 700;
}

@media (max-width: 820px) {
  .mainnav {
    display: none;
  }

  .nav-toggle {
    display: flex;
  }
}

@media (prefers-reduced-motion: reduce) {
  .navpanel,
  .navpanel.open {
    transition: none;
  }
}

/* ── Page body ──
   Top padding lives here rather than in each page head for now, so the views
   that have not been rebuilt yet keep their spacing under the sticky bar. */
.main {
  padding-top: 3rem;
}

/* ── Footer ── */
.footer {
  margin-top: 4.5rem;
  border-top: 1px solid var(--hairline);
}

.footer-inner {
  padding-top: 1.5rem;
  padding-bottom: 3rem;
  color: var(--ink-muted);
  font-size: 0.85rem;
}

.footer-inner p {
  margin: 0 0 0.4rem;
}
</style>
