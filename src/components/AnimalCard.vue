<script setup lang="ts">
import { computed, ref } from 'vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { SEX_LABEL, formatCount } from '@/lib/animals'
import type { IconName } from '@/lib/icons'
import type { Animal } from '@/types'

/** The round-photo card from the drafts. The whole card is the click target;
 *  the 查看詳情 button is the keyboard-reachable half of that.
 *
 *  Used by: HomeView.vue. */
const props = defineProps<{
  animal: Animal
  days: number | null
  /** Share of all animals in the snapshot that have been in for fewer days, 0–100. */
  percentile: number
  /** True for the single longest stay in the country, which gets its own sentence. */
  longest?: boolean
  place: string
}>()

const emit = defineEmits<{ open: [animal: Animal] }>()

const broken = ref(false)

const SEX_ICON: Record<string, IconName> = { M: 'mars', F: 'venus' }

const title = computed(() => props.animal.variety || '未填品種')

/** Floor, not round: 99.96 must not print as 100, which would read as "longer
 *  than every animal", including itself. */
const rankText = computed(() => {
  if (props.longest) return '牠是全臺等最久的那一隻'
  if (props.percentile < 1) return '剛入所，全站幾乎所有動物都等得比牠久'
  return `等得比 ${(Math.floor(props.percentile * 10) / 10).toFixed(1)}% 的動物久`
})

const badge = computed(() =>
  props.days === null ? '天數未知' : `已在所 ${formatCount(props.days)} 天`,
)
</script>

<template>
  <article class="acard" @click="emit('open', animal)">
    <span class="badge">{{ badge }}</span>
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
      <span class="place">{{ place }}</span>
      <span class="rank">
        <span class="rank-bar"><span :style="{ width: `${percentile}%` }" /></span>
        <span class="rank-txt">{{ rankText }}</span>
      </span>
      <button type="button" class="detail-btn" @click.stop="emit('open', animal)">
        查看詳情
        <LucideIcon name="arrow-right" :size="16" />
      </button>
    </div>
  </article>
</template>

<style scoped>
.acard {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  height: 100%;
  cursor: pointer;
}

/* The mask stays fixed and only the photo scales inside it, so hover never
   pushes the neighbours. */
.avatar {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-sunk);
}

.avatar img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 260ms cubic-bezier(0.4, 0, 0.2, 1);
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

/* On the card rather than the avatar: the round mask would clip it. */
.badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 3;
  padding: 0.12rem 0.7rem;
  border-radius: 999px;
  background: var(--ink);
  color: var(--plane);
  font-size: 0.76rem;
  font-variant-numeric: tabular-nums;
  outline: 3px solid var(--plane);
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

.place {
  font-size: 0.83rem;
  color: var(--ink-muted);
}

.rank {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.28rem;
  margin-top: 0.15rem;
}

.rank-bar {
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: var(--surface-sunk);
}

.rank-bar span {
  display: block;
  height: 100%;
  min-width: 3px;
  border-radius: 999px;
  background: var(--ramp-4);
}

.rank-txt {
  font-size: 0.78rem;
  color: var(--ink-muted);
  font-variant-numeric: tabular-nums;
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
}

.detail-btn svg {
  position: absolute;
  right: 1.05rem;
}

.detail-btn:hover {
  background: var(--ink);
  color: var(--plane);
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
