<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import DialogShell from '@/components/DialogShell.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { daysInShelter } from '@/composables/useAtlasData'
import { animalsLink, formatCount, monthDayLong, opensAfter, pickSiblings } from '@/lib/animals'
import type { IconName } from '@/lib/icons'
import type { Animal, Kind, Shelter } from '@/types'

const props = defineProps<{
  animal: Animal
  snapshotDate: string
  shelter?: Shelter
  /** Every animal in the snapshot; the strip of others from the same shelter
   *  is drawn from it. */
  roster: Animal[]
  /** On that shelter's own page the link to it would lead nowhere. */
  hideShelterLink?: boolean
}>()
const emit = defineEmits<{ close: []; open: [animal: Animal] }>()

const broken = ref(false)
const copied = ref(false)

const SEX: Record<string, string> = { M: '公', F: '母', N: '未填' }
const BODY: Record<string, string> = { SMALL: '小型', MEDIUM: '中型', BIG: '大型' }
const AGE: Record<string, string> = { ADULT: '成體', CHILD: '幼體' }
const STERILIZED: Record<string, string> = { T: '已絕育', F: '未絕育', N: '未登錄' }
const SEX_ICON: Record<string, IconName> = { M: 'mars', F: 'venus' }

/** How the strip's link names the list it opens: 全部 N 隻狗. For 其他 that
 *  reads 全部 N 隻動物 rather than 全部 N 隻其他. */
const KIND_WORD: Record<Kind, string> = { 狗: '狗', 貓: '貓', 其他: '動物' }

const days = computed(() => daysInShelter(props.animal.created, props.snapshotDate))

const daysText = computed(() => {
  const value = days.value
  if (value === null) return '—'
  return `${value.toLocaleString('zh-TW')} 天`
})

const yearsText = computed(() => {
  const value = days.value
  if (value === null || value < 365) return ''
  return `（約 ${(value / 365).toFixed(1)} 年）`
})

/** Against the snapshot, as on the card. The notice names the date and what
 *  to do before it, never why it is later: the data does not say. */
const notYetOpen = computed(() => opensAfter(props.animal.opendate, props.snapshotDate))

const fields = computed(() => [
  { label: '收容編號', value: props.animal.subid },
  { label: '流水號', value: props.animal.id },
  { label: '性別', value: SEX[props.animal.sex] ?? props.animal.sex },
  { label: '體型', value: BODY[props.animal.body] ?? props.animal.body },
  { label: '年齡', value: AGE[props.animal.age] ?? '未填' },
  { label: '毛色', value: props.animal.colour || '未填' },
  { label: '絕育狀態', value: STERILIZED[props.animal.sterilized] ?? props.animal.sterilized },
  {
    label: '開放認養日',
    value: notYetOpen.value
      ? `${props.animal.opendate}（尚未到）`
      : props.animal.opendate || '未填',
    marked: notYetOpen.value,
  },
  { label: '建檔日', value: props.animal.created },
])

/* ── Others of the same kind at the same shelter ───────────────────────────
 * Four picked at random each time the dialog opens or changes animal. Not in
 * the URL: a shared link promises the animal it names, not the ones beside
 * it. */

const sameKind = computed(() =>
  props.roster.filter(
    (other) =>
      other.shelter === props.animal.shelter &&
      other.kind === props.animal.kind &&
      other.id !== props.animal.id,
  ),
)

const siblings = ref<Animal[]>([])
const brokenSiblings = ref(new Set<string>())

watch(
  () => [props.animal.id, sameKind.value.length],
  () => {
    siblings.value = pickSiblings(sameKind.value, 4)
    brokenSiblings.value = new Set()
  },
  { immediate: true },
)

watch(
  () => props.animal.id,
  () => {
    broken.value = false
    copied.value = false
  },
)

function siblingDays(other: Animal): string {
  const value = daysInShelter(other.created, props.snapshotDate)
  return value === null ? '天數未知' : `${formatCount(value)} 天`
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 2000)
  } catch {
    // Clipboard access is refused in some contexts; the URL bar already shows
    // the link, so there is nothing to recover from.
  }
}
</script>

<template>
  <DialogShell
    :label="`${animal.variety || '未填品種'} 的詳細資料`"
    :reset-key="animal.id"
    @close="emit('close')"
  >
    <template #bar>
      <span class="id">收容編號 #{{ animal.subid }}</span>
      <span class="tag">公立收容所資料快照</span>
    </template>

    <div class="photo" :class="{ bare: !animal.photo || broken }">
      <img
        v-if="animal.photo && !broken"
        :src="animal.photo"
        :alt="`${animal.variety}，${SEX[animal.sex] ?? animal.sex}`"
        decoding="async"
        referrerpolicy="no-referrer"
        @error="broken = true"
      />
      <span v-else class="no-photo">{{ animal.photo ? '照片無法載入' : '無照片' }}</span>
      <span v-if="animal.photo && !broken" class="badge">
        在所 {{ days !== null && days >= 365 ? `${(days / 365).toFixed(1)} 年` : daysText }} ·
        影像原圖無裁切
      </span>
    </div>

    <div class="body">
      <div class="headline">
        <div>
          <p v-if="shelter" class="where">
            {{ shelter.county }} · {{ shelter.name }}
            <a v-if="shelter.tel" :href="`tel:${shelter.tel.replace(/[^0-9+]/g, '')}`" class="tel">
              {{ shelter.tel }}
            </a>
          </p>
          <h2>{{ animal.variety || '未填品種' }}</h2>
        </div>
        <p class="duration">
          已在所 <strong>{{ daysText }}</strong>
          <span v-if="yearsText" class="years">{{ yearsText }}</span>
        </p>
      </div>

      <p v-if="notYetOpen" class="opens">
        <LucideIcon name="calendar" :size="16" />
        <span
          ><b>這隻動物 {{ monthDayLong(animal.opendate) }}起開放認養。</b
          >在這天之前收容所可能還不受理認養，想認識牠可以先打電話詢問。</span
        >
      </p>

      <p class="section">規格化資料欄位</p>
      <dl>
        <div v-for="field in fields" :key="field.label" :class="{ marked: field.marked }">
          <dt>{{ field.label }}</dt>
          <dd>{{ field.value }}</dd>
        </div>
      </dl>

      <template v-if="animal.remark">
        <p class="section">收容所備註</p>
        <p class="remark">{{ animal.remark }}</p>
      </template>

      <template v-if="siblings.length">
        <p class="section">同一間收容所的浪浪們</p>
        <div class="here">
          <ul class="strip">
            <li v-for="other in siblings" :key="other.id">
              <button type="button" class="mini" @click="emit('open', other)">
                <span class="thumb">
                  <img
                    v-if="other.photo && !brokenSiblings.has(other.id)"
                    :src="other.photo"
                    alt=""
                    loading="lazy"
                    decoding="async"
                    referrerpolicy="no-referrer"
                    @error="brokenSiblings = new Set(brokenSiblings).add(other.id)"
                  />
                  <span v-else class="thumb-empty">{{
                    other.photo ? '照片無法載入' : '無照片'
                  }}</span>
                </span>
                <span class="mini-days">{{ siblingDays(other) }}</span>
                <span class="mini-name">
                  <LucideIcon
                    :name="SEX_ICON[other.sex] ?? 'circle-help'"
                    :size="13"
                    :label="SEX[other.sex] ?? '未填'"
                  />
                  {{ other.variety || '未填品種' }}
                </span>
              </button>
            </li>
          </ul>
          <div class="strip-foot">
            <RouterLink v-if="shelter && !hideShelterLink" :to="`/shelters/${shelter.id}`">
              收容所介紹 →
            </RouterLink>
            <RouterLink
              :to="animalsLink({ shelter: animal.shelter, kind: animal.kind })"
              class="all"
            >
              看這裡的全部 {{ formatCount(sameKind.length + 1) }} 隻{{ KIND_WORD[animal.kind] }} →
            </RouterLink>
          </div>
        </div>
      </template>

      <p class="note">
        ※
        欄位內容依各收容所登錄實務而異，未填不代表該項目不存在或未施作。實際健康與個性務必以現場互動評估為準。
      </p>

      <footer class="actions">
        <button type="button" class="chip small" @click="copyLink">
          {{ copied ? '連結已複製' : '複製此動物頁面連結' }}
        </button>
        <button type="button" class="chip small on" @click="emit('close')">關閉</button>
      </footer>
    </div>
  </DialogShell>
</template>

<style scoped>
.id {
  font-size: 0.85rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;
}

.tag {
  padding: 0.08rem 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);
  font-size: 0.74rem;
  color: var(--ink-muted);
}

.photo {
  position: relative;
  aspect-ratio: 3 / 2;
  background: var(--surface-sunk);
  display: grid;
  place-items: center;

  /* A 3:2 void is a lot of nothing when there is no photo to put in it. */
  &.bare {
    aspect-ratio: auto;
    min-height: 5.5rem;
  }

  & img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    /* contain, not cover: cropping an animal out of its own portrait is worse
     than a band of empty surface beside it. */
    object-fit: contain;
  }
}

.no-photo {
  font-size: 0.9rem;
  color: var(--ink-muted);
}

.badge {
  position: absolute;
  top: 0.6rem;
  left: 0.6rem;
  padding: 0.12rem 0.55rem;
  border-radius: var(--radius-sm);
  background: var(--surface);
  border: 1px solid var(--hairline);
  font-size: 0.74rem;
  color: var(--ink-secondary);
}

.body {
  padding: 1.25rem 1.4rem 1.4rem;
}

.headline {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.5rem;
  flex-wrap: wrap;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--hairline);
}

.where {
  margin: 0;
  font-size: 0.82rem;
  color: var(--ink-muted);
}

/* Tappable on a phone, which is where someone reading this is most likely to
   act on it. */
.tel {
  margin-left: 0.5rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;
}

.body h2 {
  margin: 0.15rem 0 0;
  font-size: 1.45rem;
}

.duration {
  margin: 0;
  font-size: 0.95rem;
  color: var(--accent-text);

  & strong {
    font-size: 1.45rem;
    font-variant-numeric: tabular-nums;
  }
}

.years {
  color: var(--ink-muted);
  font-size: 0.85rem;
}

.opens {
  display: flex;
  gap: 0.55rem;
  margin: 1rem 0 0;
  padding: 0.7rem 0.9rem;
  border-left: 3px solid var(--ramp-4);
  border-radius: var(--radius-sm);
  background: var(--surface-sunk);
  color: var(--ink-secondary);
  font-size: 0.9rem;
  line-height: 1.6;

  & svg {
    flex-shrink: 0;
    margin-top: 0.2rem;
    color: var(--accent-text);
  }

  & b {
    color: var(--ink);
  }
}

dl > div.marked {
  background: var(--surface-sunk);
}

.section {
  margin: 1.1rem 0 0.5rem;
  font-size: 0.8rem;
  color: var(--ink-muted);
}

dl {
  margin: 0;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  overflow: hidden;
}

dl > div {
  padding: 0.6rem 0.9rem;
  border-right: 1px solid var(--hairline);
  border-bottom: 1px solid var(--hairline);
}

dt {
  font-size: 0.76rem;
  color: var(--ink-muted);
  margin-bottom: 0.1rem;
}

dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.remark {
  margin: 0;
  padding: 0.75rem 0.9rem;
  background: var(--surface-sunk);
  border-radius: var(--radius-sm);
  font-size: 0.92rem;
  white-space: pre-wrap;
}

/* ── Same shelter strip ── */
.here {
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.8rem;
  margin: 0;
  padding: 0.9rem;
  list-style: none;
}

.mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  color: var(--ink-secondary);
  font: inherit;
  font-size: 0.78rem;
  line-height: 1.5;
  cursor: pointer;

  &:hover .thumb img {
    transform: scale(1.06);
  }
}

.thumb {
  position: relative;
  width: 76%;
  aspect-ratio: 1 / 1;
  margin-bottom: 0.4rem;
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

.thumb-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--ink-muted);
  font-size: 0.7rem;
}

.mini-days {
  color: var(--accent-text);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.mini-name {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;

  & svg {
    flex-shrink: 0;
    color: var(--ink-muted);
  }
}

.strip-foot {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.4rem 1rem;
  padding: 0.55rem 0.9rem;
  border-top: 1px solid var(--hairline);
  font-size: 0.84rem;

  & a {
    color: var(--accent-text);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  & .all {
    margin-left: auto;
  }
}

.note {
  margin: 1.1rem 0 0;
  padding-top: 1rem;
  border-top: 1px solid var(--hairline);
  font-size: 0.8rem;
  line-height: 1.7;
  color: var(--ink-muted);
}

.actions {
  margin-top: 1.1rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

@media (max-width: 520px) {
  .strip {
    gap: 0.4rem;
    padding: 0.75rem 0.5rem;
  }

  .mini {
    font-size: 0.7rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .thumb img {
    transition: none;
  }

  .mini:hover .thumb img {
    transform: none;
  }
}
</style>
