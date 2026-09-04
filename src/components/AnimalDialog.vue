<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { daysInShelter } from '@/composables/useAtlasData'
import type { Animal, Shelter } from '@/types'

const props = defineProps<{ animal: Animal; snapshotDate: string; shelter?: Shelter }>()
const emit = defineEmits<{ close: [] }>()

const panel = ref<HTMLElement | null>(null)
const broken = ref(false)
const copied = ref(false)

const SEX: Record<string, string> = { M: '公', F: '母', N: '未填' }
const BODY: Record<string, string> = { SMALL: '小型', MEDIUM: '中型', BIG: '大型' }
const AGE: Record<string, string> = { ADULT: '成體', CHILD: '幼體' }
const STERILIZED: Record<string, string> = { T: '已絕育', F: '未絕育', N: '未登錄' }

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  document.addEventListener('keydown', onKey)
  // Stop the list behind the dialog from scrolling under it.
  document.body.style.overflow = 'hidden'
  panel.value?.focus()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})

watch(
  () => props.animal.id,
  () => {
    broken.value = false
    copied.value = false
  },
)

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

const fields = computed(() => [
  { label: '收容編號', value: props.animal.subid },
  { label: '流水號', value: props.animal.id },
  { label: '性別', value: SEX[props.animal.sex] ?? props.animal.sex },
  { label: '體型', value: BODY[props.animal.body] ?? props.animal.body },
  { label: '年齡', value: AGE[props.animal.age] ?? '未填' },
  { label: '毛色', value: props.animal.colour || '未填' },
  { label: '絕育狀態', value: STERILIZED[props.animal.sterilized] ?? props.animal.sterilized },
  { label: '開放認養日', value: props.animal.opendate || '未填' },
  { label: '建檔日', value: props.animal.created },
])

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
  <Teleport to="body">
    <div class="backdrop" @click.self="emit('close')">
      <div
        ref="panel"
        class="dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="`${animal.variety || '未填品種'} 的詳細資料`"
        tabindex="-1"
      >
        <header class="bar">
          <span class="id">收容編號 #{{ animal.subid }}</span>
          <span class="tag">公立收容所資料快照</span>
          <button type="button" class="close" aria-label="關閉" @click="emit('close')">×</button>
        </header>

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

          <p class="section">規格化資料欄位</p>
          <dl>
            <div v-for="field in fields" :key="field.label">
              <dt>{{ field.label }}</dt>
              <dd>{{ field.value }}</dd>
            </div>
          </dl>

          <template v-if="animal.remark">
            <p class="section">收容所備註</p>
            <p class="remark">{{ animal.remark }}</p>
          </template>

          <p class="note">
            ※ 欄位內容依各收容所登錄實務而異，未填不代表該項目不存在或未施作。實際健康與個性務必以現場互動評估為準。
          </p>

          <footer class="actions">
            <button type="button" class="chip small" @click="copyLink">
              {{ copied ? '連結已複製' : '複製此動物頁面連結' }}
            </button>
            <button type="button" class="chip small on" @click="emit('close')">關閉</button>
          </footer>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(20, 16, 12, 0.55);
  display: grid;
  place-items: center;
  padding: 1.5rem;
  z-index: 50;
}

.dialog {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  width: min(720px, 100%);
  max-height: min(90vh, 860px);
  overflow: auto;
  outline: none;
}

.bar {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 0.9rem 0.7rem 1.25rem;
  background: var(--surface);
  border-bottom: 1px solid var(--hairline);
}

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

.close {
  margin-left: auto;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  border: 0;
  background: none;
  color: var(--ink-secondary);
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
}

.close:hover {
  background: var(--surface-sunk);
  color: var(--ink);
}

.photo {
  position: relative;
  aspect-ratio: 3 / 2;
  background: var(--surface-sunk);
  display: grid;
  place-items: center;
}

/* A 3:2 void is a lot of nothing when there is no photo to put in it. */
.photo.bare {
  aspect-ratio: auto;
  min-height: 5.5rem;
}

.photo img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  /* contain, not cover: cropping an animal out of its own portrait is worse
     than a band of empty surface beside it. */
  object-fit: contain;
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
}

.duration strong {
  font-size: 1.45rem;
  font-variant-numeric: tabular-nums;
}

.years {
  color: var(--ink-muted);
  font-size: 0.85rem;
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
</style>
