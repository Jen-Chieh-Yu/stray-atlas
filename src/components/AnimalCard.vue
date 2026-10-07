<script setup lang="ts">
import { computed, ref } from 'vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { SEX_LABEL, formatCount, monthDay, opensAfter } from '@/lib/animals'
import type { IconName } from '@/lib/icons'
import type { Animal } from '@/types'

/** The round-photo card from the drafts. The whole card is the click target;
 *  the 查看詳情 button is the keyboard-reachable half of that.
 *
 *  Used by: HomeView.vue, AnimalsView.vue and ShelterView.vue. */
const props = defineProps<{
  animal: Animal
  days: number | null
  place: string
  /** For the 開放認養 badge, which compares against the snapshot like 已在所. */
  snapshotDate: string
}>()

const emit = defineEmits<{ open: [animal: Animal] }>()

const broken = ref(false)

const SEX_ICON: Record<string, IconName> = { M: 'mars', F: 'venus' }

const title = computed(() => props.animal.variety || '未填品種')

/** The date only, never a reason: a later 開放認養日 can be a claim period,
 *  a medical hold or paperwork, and the data does not say which. */
const opens = computed(() =>
  opensAfter(props.animal.opendate, props.snapshotDate) ? monthDay(props.animal.opendate) : null,
)

/* ── Shelter name: one line, the full name on demand ───────────────────────
 * Cut with an ellipsis so every card keeps the same height. The full name
 * stays in the DOM (screen readers read it whole) and in `title`; the dark
 * tip below repeats it for pointer and keyboard users, and only when the
 * name was actually cut. Touch has no hover: the dialog shows it in full. */

const placeEl = ref<HTMLElement | null>(null)
const tip = ref(false)

function showTip() {
  const el = placeEl.value
  tip.value = !!el && el.scrollWidth > el.clientWidth
}

function hideTip() {
  tip.value = false
}

function onButtonFocus(event: FocusEvent) {
  if ((event.target as HTMLElement).matches(':focus-visible')) showTip()
}
</script>

<template>
  <article class="acard" @click="emit('open', animal)">
    <!-- The words in .full drop on a narrow card, where 在所 / 開放 is all
         that fits two to a row. -->
    <div class="badges">
      <span class="badge">
        <template v-if="days === null">天數未知</template>
        <template v-else><span class="full">已</span>在所 {{ formatCount(days) }} 天</template>
      </span>
      <span v-if="opens" class="badge opens">{{ opens }} 開放<span class="full">認養</span></span>
    </div>
    <div class="avatar">
      <img
        v-if="animal.photo && !broken"
        :src="animal.photo"
        :alt="`${title}，${SEX_LABEL[animal.sex] ?? '性別未填'}`"
        loading="lazy"
        decoding="async"
        referrerpolicy="no-referrer"
        @error="broken = true"
      />
      <span v-else class="fallback">{{ animal.photo ? '照片無法載入' : '無照片' }}</span>
    </div>

    <div class="body">
      <h3 class="title">
        <LucideIcon
          :name="SEX_ICON[animal.sex] ?? 'circle-help'"
          :size="16"
          :label="SEX_LABEL[animal.sex] ?? '未填'"
          class="sex"
        />
        {{ title }}
      </h3>
      <span class="place-wrap">
        <span
          ref="placeEl"
          class="place"
          :title="place"
          @mouseenter="showTip"
          @mouseleave="hideTip"
          >{{ place }}</span
        >
        <span v-if="tip" class="tip" aria-hidden="true">{{ place }}</span>
      </span>
      <!-- The number the shelter knows this animal by, which is what a visitor
           quotes on the phone. The rule above it is a divider only; it used to
           be a rank bar (2026-09-29). -->
      <span class="ident">
        <span class="rule" />
        <span class="subid"><span class="k">收容編號</span> {{ animal.subid }}</span>
      </span>
      <button
        type="button"
        class="detail-btn"
        @click.stop="emit('open', animal)"
        @focus="onButtonFocus"
        @blur="hideTip"
      >
        查看詳情
        <LucideIcon name="arrow-right" :size="16" />
      </button>
    </div>
  </article>
</template>

<style scoped>
/* min-width: 0 lets a grid or flex track shrink the card below its one-line
   shelter name; without it the nowrap text widens the column instead. The
   container is what the badges measure to decide whether two fit side by
   side. */
.acard {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  height: 100%;
  min-width: 0;
  cursor: pointer;
  container-type: inline-size;
}

/* The mask stays fixed and only the photo scales inside it, so hover never
   pushes the neighbours. */
.avatar {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-sunk);

  & img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 260ms cubic-bezier(0.4, 0, 0.2, 1);
  }
}

.acard:hover .avatar img {
  transform: scale(1.06);
}

.fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-muted);
  font-size: 0.85rem;
}

/* On the card rather than the avatar: the round mask would clip them. A wide
   card lays the row over the photo's top edge, 已在所 at the left end and
   開放認養 at the right. */
.badges {
  position: absolute;
  top: 10px;
  right: 10px;
  left: 10px;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  pointer-events: none;
}

.badge {
  padding: 0.12rem 0.7rem;
  border-radius: 999px;
  background: var(--ink);
  color: var(--plane);
  font-size: 0.76rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  outline: 3px solid var(--plane);

  /* Light on dark the other way round, so it never reads as a second
     已在所 figure; a step larger and bold so it is not passed over. */
  &.opens {
    padding: 0.16rem 0.75rem;
    border: 1.5px solid var(--ink);
    background: var(--surface);
    color: var(--ink);
    font-size: 0.84rem;
    font-weight: 600;
  }
}

/* Two-column phone cards: the row leaves the photo for the space above the
   breed, centred when alone and evenly spaced when two. Both badges take the
   same size and border so every card's row is one height and the breeds in a
   grid row line up. The longest pair on 2026-10-04 (在所 134 天, 10/09 開放)
   fits the 144px card of a 360px phone; a longer one wraps rather than
   overflowing. */
@container (max-width: 250px) {
  .badges {
    position: static;
    order: 1;
    flex-wrap: wrap;
    justify-content: space-evenly;
    gap: 2px;
  }

  .body {
    order: 2;
  }

  .badge,
  .badge.opens {
    padding: 0.08rem 0.35rem;
    border: 1.5px solid var(--ink);
    font-size: 0.7rem;
    outline: 0;
  }

  .full {
    display: none;
  }
}

.body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0 0.25rem;
  text-align: center;
}

.title {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  font-size: 1.02rem;
  font-weight: 700;
}

/* Sex is told apart by shape only: --series-a/b are reserved for dogs and cats
   drawn as two series (DESIGN.md §3). */
.sex {
  flex-shrink: 0;
  color: var(--ink-muted);
}

.place-wrap {
  position: relative;
  display: flex;
  justify-content: center;
  min-width: 0;
}

.place {
  overflow: hidden;
  font-size: 0.83rem;
  color: var(--ink-muted);
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* Below the name, over the divider, and no wider than the card: a card at
   either end of the home page's scrolling strip would otherwise have it
   clipped. */
.tip {
  position: absolute;
  top: calc(100% + 4px);
  left: 50%;
  z-index: 4;
  width: max-content;
  max-width: 100%;
  padding: 0.3rem 0.6rem;
  border-radius: var(--radius-sm);
  background: var(--ink);
  color: var(--plane);
  font-size: 0.8rem;
  line-height: 1.45;
  transform: translateX(-50%);
  pointer-events: none;
}

.ident {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.28rem;
  margin-top: 0.15rem;
}

.rule {
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: var(--ramp-4);
}

/* Tabular so numbers of different lengths in one row do not jitter; the label
   wraps above the number on a narrow card rather than cutting the number. */
.subid {
  font-size: 0.8rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;

  & .k {
    color: var(--ink-muted);
  }
}

.detail-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: auto;
  padding: 0.45rem 2.4rem;
  border: 1px solid var(--ink);
  border-radius: 999px;
  background: transparent;
  color: var(--ink);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background 160ms ease,
    color 160ms ease;

  & svg {
    position: absolute;
    right: 1.05rem;
  }

  &:hover {
    background: var(--ink);
    color: var(--plane);
  }
}

/* A phone card is too narrow for the wide padding that keeps the arrow clear
   of the centred label: at 144px the label wrapped to two lines. Here the
   arrow follows the label instead, and the pair stays on one line. */
@container (max-width: 250px) {
  .detail-btn {
    gap: 0.3rem;
    padding-inline: 0.5rem;
    white-space: nowrap;

    & svg {
      position: static;
    }
  }
}

@media (prefers-reduced-motion: reduce) {
  .avatar img {
    transition: none;
  }

  .acard:hover .avatar img {
    transform: none;
  }
}
</style>
