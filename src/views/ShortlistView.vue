<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AnimalDialog from '@/components/AnimalDialog.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import MissingAnimalDialog from '@/components/MissingAnimalDialog.vue'
import PageHead from '@/components/PageHead.vue'
import { useRoster } from '@/composables/useRoster'
import { useShortlist } from '@/composables/useShortlist'
import { SEX_LABEL, formatCount, isNewerId, monthDay, opensAfter } from '@/lib/animals'
import { closeAnimalDialog } from '@/lib/dialogRoute'
import type { IconName } from '@/lib/icons'
import { fadeIn, fadeOut, foldAway, unfold } from '@/lib/motion'
import { addressesOf, phoneOf } from '@/lib/shelters'
import { groupByShelter, shortlistText } from '@/lib/shortlist'
import type { ShortlistEntry } from '@/lib/shortlist'
import type { Animal } from '@/types'

/** /shortlist: the animals a visitor marked, grouped by shelter for phoning.
 *
 *  An animal still on the roster is shown as it is today; one that has left
 *  is shown from what was saved when it was added, under the same words the
 *  不在目前名單 dialog uses, never 已被認養 (DESIGN.md §15). */

const route = useRoute()
const router = useRouter()
const { animals, snapshotDate, loading, error, shelterById, daysOf } = useRoster()
const shortlist = useShortlist()

const SEX_ICON: Record<string, IconName> = { M: 'mars', F: 'venus' }

const byId = computed(() => new Map(animals.value.map((animal) => [animal.id, animal])))
const current = (id: string) => byId.value.get(id) ?? null

/** Shelters keep the order they had once the roster loaded: removing an
 *  animal never moves a group under the pointer, and 復原 puts one back where
 *  it was. The next visit sorts afresh. */
const order = ref<string[] | null>(null)

const groups = computed(() => {
  const sorted = groupByShelter(shortlist.entries.value, (id) => shelterById.value.get(id)?.name)
  if (!order.value) return sorted
  const rank = new Map(order.value.map((id, at) => [id, at]))
  const last = rank.size
  return sorted.sort((a, b) => (rank.get(a.shelter) ?? last) - (rank.get(b.shelter) ?? last))
})

watch(
  [loading, groups],
  () => {
    if (!order.value && !loading.value) order.value = groups.value.map((group) => group.shelter)
  },
  { immediate: true },
)
const listedCount = computed(
  () => shortlist.entries.value.filter((entry) => byId.value.has(entry.id)).length,
)

/** Each group with its shelter's address and phone as they are today, and
 *  each entry with the animal it still is on the roster, or null. */
const view = computed(() =>
  groups.value.map((group) => {
    const shelter = shelterById.value.get(group.shelter)
    return {
      ...group,
      address: shelter ? (addressesOf(shelter)[0]?.text ?? '') : '',
      phone: shelter ? phoneOf(shelter) : null,
      rows: group.entries.map((entry) => ({ entry, animal: current(entry.id) })),
    }
  }),
)

function metaOf(animal: Animal): string {
  const days = daysOf(animal)
  return [
    animal.subid ? `收容編號 ${animal.subid}` : `流水號 ${animal.id}`,
    days === null ? '' : `已在所 ${formatCount(days)} 天`,
    opensAfter(animal.opendate, snapshotDate.value)
      ? `${monthDay(animal.opendate)} 起開放認養`
      : '',
  ]
    .filter(Boolean)
    .join(' · ')
}

/* ── Removing, with one step back ──────────────────────────────────────────
 * 移除 asks nothing, since 復原 undoes it; only 清空清單 asks first. The row
 * fades and folds away (motion.ts), and 復原 opens it up again. */

const removed = ref<{ entry: ShortlistEntry; index: number } | null>(null)

function remove(id: string) {
  removed.value = shortlist.remove(id)
}

function undo() {
  if (removed.value) shortlist.restore(removed.value.entry, removed.value.index)
  removed.value = null
}

function clearAll() {
  const total = shortlist.count.value
  if (window.confirm(`要清空候選清單嗎？清單裡的 ${total} 隻都會移除，無法復原。`)) {
    shortlist.clear()
    removed.value = null
  }
}

/* ── 複製收容編號 and 列印 ── */

const copied = ref(false)
const manual = ref(false)
const manualEl = ref<HTMLTextAreaElement | null>(null)

const listText = computed(() =>
  shortlistText(
    groups.value,
    (id) => shelterById.value.get(id)?.tel,
    (id) => byId.value.has(id),
    snapshotDate.value,
  ),
)

async function copy() {
  try {
    await navigator.clipboard.writeText(listText.value)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 2000)
  } catch {
    manual.value = true
    await nextTick()
    manualEl.value?.select()
  }
}

function print() {
  window.print()
}

/* ── The detail dialog, as on the other lists ── */

const openAnimal = computed<Animal | null>(() => {
  const id = route.query.animal
  return typeof id === 'string' ? current(id) : null
})

const missingId = computed(() => {
  const id = route.query.animal
  if (typeof id !== 'string' || animals.value.length === 0 || openAnimal.value) return null
  return id
})

function open(animal: Animal) {
  void router.push({ query: { ...route.query, animal: animal.id } })
}

function close() {
  closeAnimalDialog(router, route)
}
</script>

<template>
  <div class="shortlist">
    <PageHead title="候選清單">
      你在這個瀏覽器裡標記的動物，依收容所分組，方便一間一間打電話詢問。
    </PageHead>

    <p v-if="loading" class="state">載入中…</p>
    <p v-else-if="error" class="state">資料載入失敗（{{ error }}）。</p>

    <!-- The list and the empty state fade into each other, so removing the
         last animal or 清空清單 does not snap the page. -->
    <Transition v-else mode="out-in" :css="false" @enter="fadeIn" @leave="fadeOut">
      <div v-if="shortlist.count.value === 0" class="empty">
        <p>還沒有加入任何動物。在找動物頁的卡片上按書籤鈕，就會加進來。</p>
        <RouterLink to="/animals" class="chip">
          前往找動物 <LucideIcon name="arrow-right" :size="14" />
        </RouterLink>
        <p v-if="removed" class="undo">
          已移除 {{ removed.entry.variety || '未填品種' }}（{{
            removed.entry.subid || removed.entry.id
          }}）。<button type="button" @click="undo">復原</button>
        </p>
      </div>

      <div v-else>
        <div class="tools no-print">
          <span class="count" aria-live="polite">
            共 <b>{{ formatCount(shortlist.count.value) }}</b> 隻，{{ formatCount(listedCount) }}
            隻仍在目前名單
          </span>
          <button type="button" class="chip" :class="{ done: copied }" @click="copy">
            <LucideIcon v-if="copied" name="check" :size="14" />
            {{ copied ? '已複製' : '複製收容編號' }}
          </button>
          <button type="button" class="chip" @click="print">列印</button>
          <button type="button" class="chip" @click="clearAll">清空清單</button>
        </div>

        <p v-if="removed" class="undo no-print" role="status">
          已移除 {{ removed.entry.variety || '未填品種' }}（{{
            removed.entry.subid || removed.entry.id
          }}）。<button type="button" @click="undo">復原</button>
        </p>

        <div v-if="manual" class="manual no-print">
          <label for="list-text"
            >瀏覽器沒有讓本站寫入剪貼簿，請自行複製下面這段（已全選，按 Ctrl+C 或長按）：</label
          >
          <textarea id="list-text" ref="manualEl" readonly rows="8" :value="listText" />
        </div>

        <p class="print-only">StrayAtlas 候選清單（{{ snapshotDate }} 資料）</p>

        <TransitionGroup tag="div" :css="false" @enter="unfold" @leave="foldAway">
          <section
            v-for="group in view"
            :key="group.shelter"
            class="group"
            :aria-label="group.name"
          >
            <header class="ghead">
              <h2>{{ group.name }}</h2>
              <span v-if="group.address" class="addr">{{ group.address }}</span>
              <a v-if="group.phone?.href" :href="group.phone.href" class="tel">
                <LucideIcon name="phone" :size="14" />
                {{ group.phone.text }}
              </a>
              <span v-else-if="group.phone" class="addr">{{ group.phone.text }}</span>
              <span class="n">{{ group.entries.length }} 隻</span>
            </header>

            <TransitionGroup tag="ul" class="rows" :css="false" @enter="unfold" @leave="foldAway">
              <li
                v-for="{ entry, animal } in group.rows"
                :key="entry.id"
                class="row"
                :class="{ gone: !animal }"
              >
                <template v-if="animal">
                  <img
                    v-if="animal.photo"
                    :src="animal.photo"
                    alt=""
                    class="thumb"
                    loading="lazy"
                    referrerpolicy="no-referrer"
                  />
                  <span v-else class="thumb none">無照片</span>
                  <div class="info">
                    <p class="name">
                      <LucideIcon
                        :name="SEX_ICON[animal.sex] ?? 'circle-help'"
                        :size="15"
                        :label="SEX_LABEL[animal.sex] ?? '未填'"
                      />
                      {{ animal.variety || '未填品種' }}
                    </p>
                    <p class="meta">{{ metaOf(animal) }}</p>
                  </div>
                  <span class="btns no-print">
                    <button type="button" class="chip small" @click="open(animal)">查看詳情</button>
                    <button type="button" class="chip small" @click="remove(entry.id)">移除</button>
                  </span>
                </template>

                <template v-else>
                  <span class="thumb none">不在名單</span>
                  <div class="info">
                    <p class="name">
                      <LucideIcon
                        :name="SEX_ICON[entry.sex] ?? 'circle-help'"
                        :size="15"
                        :label="SEX_LABEL[entry.sex] ?? '未填'"
                      />
                      {{ entry.variety || '未填品種' }}
                      <span class="tag">不在目前名單</span>
                    </p>
                    <p class="meta">
                      {{ entry.subid ? `收容編號 ${entry.subid}` : `流水號 ${entry.id}` }} ·
                      {{ monthDay(entry.added) }}
                      加入時的資料。牠不在目前開放認養的名單裡，可能已被認養、轉所或暫停開放認養，本站無法分辨；想確認請致電收容所。
                    </p>
                  </div>
                  <span class="btns no-print">
                    <button type="button" class="chip small" @click="remove(entry.id)">移除</button>
                  </span>
                </template>
              </li>
            </TransitionGroup>
          </section>
        </TransitionGroup>

        <p class="foot">
          前往收容所前，請先致電確認動物仍在所內，並依各收容所的規定辦理認養。本站不辦理認養。
        </p>
      </div>
    </Transition>

    <AnimalDialog
      v-if="openAnimal"
      :animal="openAnimal"
      :snapshot-date="snapshotDate"
      :shelter="shelterById.get(openAnimal.shelter)"
      :roster="animals"
      @close="close"
      @open="open"
    />
    <MissingAnimalDialog
      v-else-if="missingId"
      :id="missingId"
      :newer="isNewerId(missingId, animals)"
      @close="close"
      @browse="router.push('/animals')"
    />
  </div>
</template>

<style scoped>
.state {
  margin-top: 2rem;
  color: var(--ink-muted);
}

.empty {
  margin-top: 2rem;
  padding: 2rem 1.5rem;
  border: 1px dashed var(--hairline);
  border-radius: var(--radius);
  text-align: center;

  & p {
    margin: 0 0 1rem;
    color: var(--ink-secondary);
  }

  & .undo {
    margin: 1rem 0 0;
  }
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  text-decoration: none;

  &.done {
    border-color: var(--ramp-3);
    color: var(--ink);
  }
}

.tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin: 1.5rem 0 1rem;

  & .count {
    margin-right: auto;

    & b {
      color: var(--accent-text);
    }
  }
}

.undo {
  margin: 0 0 1rem;
  font-size: 0.88rem;
  color: var(--ink-secondary);

  & button {
    padding: 0;
    border: 0;
    background: none;
    color: var(--accent-text);
    font: inherit;
    text-decoration: underline;
    cursor: pointer;
  }
}

.manual {
  margin: 0 0 1rem;

  & label {
    display: block;
    margin-bottom: 0.4rem;
    font-size: 0.8rem;
    color: var(--ink-secondary);
  }

  & textarea {
    width: 100%;
    padding: 0.5rem 0.65rem;
    border: 1.5px solid var(--ramp-3);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    font-size: 0.85rem;
    line-height: 1.65;
    resize: vertical;
  }
}

.group {
  margin-bottom: 1rem;
  padding: 0.9rem 1.2rem;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
}

.ghead {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.2rem 1rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--hairline);

  & h2 {
    margin: 0;
    font-size: 1.05rem;
  }

  & .addr,
  & .n {
    color: var(--ink-muted);
    font-size: 0.82rem;
  }

  & .tel {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    color: var(--accent-text);
    font-weight: 700;
    font-size: 0.88rem;
  }
}

.rows {
  margin: 0;
  padding: 0;
  list-style: none;
}

.row {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  gap: 0.8rem;
  align-items: center;
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--hairline);

  &:last-child {
    border-bottom: 0;
  }

  & p {
    margin: 0;
  }
}

.thumb {
  width: 56px;
  height: 56px;
  border-radius: 999px;
  object-fit: cover;

  &.none {
    display: grid;
    place-items: center;
    background: var(--surface-sunk);
    color: var(--ink-muted);
    font-size: 0.66rem;
    text-align: center;
  }
}

.name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  font-weight: 700;

  & svg {
    color: var(--ink-muted);
  }
}

.meta {
  margin-top: 0.15rem !important;
  color: var(--ink-secondary);
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
}

.gone {
  & .name {
    color: var(--ink-secondary);
  }

  & .meta {
    color: var(--ink-muted);
  }
}

/* The same dark state tag as the 不在目前名單 dialog. */
.tag {
  padding: 0 0.4rem;
  border-radius: var(--radius-sm);
  background: var(--ink-secondary);
  color: var(--surface);
  font-size: 0.7rem;
  font-weight: 400;
}

.btns {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.4rem;
}

.foot {
  margin-top: 1rem;
  color: var(--ink-muted);
  font-size: 0.82rem;
}

.print-only {
  display: none;
}

@media (max-width: 560px) {
  .row {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .thumb {
    width: 48px;
    height: 48px;
  }

  .btns {
    grid-column: 2;
    justify-content: flex-start;
  }
}

/* What a printout needs: each shelter, its phone and the numbers to quote. */
@media print {
  .no-print {
    display: none !important;
  }

  .print-only {
    display: block;
    font-weight: 700;
  }

  .group {
    break-inside: avoid;
    border-color: #999;
  }
}
</style>
