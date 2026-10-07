<script setup lang="ts">
import { RouterLink } from 'vue-router'
import DialogShell from '@/components/DialogShell.vue'
import LucideIcon from '@/components/LucideIcon.vue'
import { OFFICIAL_ADOPTION_URL } from '@/lib/animals'

/** What a ?animal=<id> link shows when that animal is not in the roster.
 *
 *  The usual case is a link shared days ago whose animal has since left the
 *  list. Why it left is not in the data — adopted, transferred, withdrawn and
 *  died all look the same — so the text lists the possibilities and claims
 *  none of them (CLAUDE.md §1.1). Nothing about the animal is shown because
 *  nothing is kept: the site holds today's roster only.
 *
 *  Used by: HomeView.vue, AnimalsView.vue and ShelterView.vue. */
defineProps<{
  id: string
  /** The 流水號 is above every one in the roster (isNewerId). */
  newer: boolean
}>()
const emit = defineEmits<{ close: []; browse: [] }>()
</script>

<template>
  <DialogShell label="不在目前名單裡的動物" @close="emit('close')">
    <template #bar>
      <span class="id">{{ /^\d+$/.test(id) ? '流水號' : '編號' }} #{{ id }}</span>
      <span class="tag">不在目前名單</span>
    </template>

    <div class="band">
      <LucideIcon name="image-off" :size="26" />
      本站目前沒有這隻動物的資料
    </div>

    <div class="notice" role="status">
      <span class="icon"><LucideIcon name="search-x" :size="18" /></span>
      <div>
        <p><b>這隻動物不在目前開放認養的名單裡。</b></p>
        <p class="more">
          牠可能已被認養、轉到其他收容所或暫停開放認養，也可能是連結不完整；本站無法分辨是哪一種。想確認牠的狀況，請致電收容所，或到
          <a :href="OFFICIAL_ADOPTION_URL" target="_blank" rel="noreferrer"
            >農業部動物認領養公告頁（pet.gov.tw）</a
          >
          查詢。
        </p>
        <p v-if="newer" class="newer">
          這個編號比目前名單裡的都新，可能是剛建檔、本站還沒更新到。本站每天早上更新一次。
        </p>
      </div>
    </div>
    <!-- A lost pet is the other common reason to arrive here with a number;
         the note on the find-animals page says where else to look. -->
    <p class="lost">
      在找走失的寵物？剛進收容所的動物通常還不在名單上，<RouterLink
        :to="{ path: '/animals', hash: '#lost' }"
        >看怎麼找 →</RouterLink
      >
    </p>

    <footer class="actions">
      <button type="button" class="chip small" @click="emit('browse')">
        看目前仍在所的動物 <LucideIcon name="arrow-right" :size="14" />
      </button>
      <button type="button" class="chip small on" @click="emit('close')">關閉</button>
    </footer>
  </DialogShell>
</template>

<style scoped>
.id {
  font-size: 0.85rem;
  color: var(--ink-secondary);
  font-variant-numeric: tabular-nums;
}

/* Dark rather than the usual sunk tag: it replaces 公立收容所資料快照 and has
   to read as a state, not a label. */
.tag {
  padding: 0.08rem 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--ink-secondary);
  font-size: 0.74rem;
  color: var(--surface);
  white-space: nowrap;
}

/* Where the photo would be, so the dialog still reads as "an animal goes
   here". */
.band {
  display: grid;
  place-items: center;
  gap: 0.2rem;
  min-height: 5.5rem;
  padding: 1rem;
  background: var(--surface-sunk);
  color: var(--ink-muted);
  font-size: 0.9rem;
  text-align: center;

  & svg {
    opacity: 0.7;
  }
}

.notice {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.9rem 1.25rem;
  background: var(--surface-sunk);
  border-top: 1px solid var(--hairline);
  border-bottom: 1px solid var(--hairline);

  & p {
    margin: 0;
    font-size: 0.92rem;
    color: var(--ink-secondary);
  }

  & b {
    color: var(--ink);
  }

  & a {
    color: var(--accent-text);
  }
}

.icon {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--ink-secondary);
}

.notice .more {
  margin-top: 0.35rem;
  font-size: 0.86rem;
}

.notice .newer {
  margin-top: 0.5rem;
  padding: 0.4rem 0.7rem;
  border-left: 3px solid var(--ramp-3);
  background: var(--surface);
  font-size: 0.84rem;
}

.lost {
  margin: 0;
  padding: 0.75rem 1.25rem 0;
  color: var(--ink-secondary);
  font-size: 0.86rem;

  & a {
    color: var(--accent-text);
  }
}

.actions {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem 1rem;
  flex-wrap: wrap;
  padding: 1.1rem 1.25rem 1.2rem;
}

.chip svg {
  vertical-align: -2px;
}
</style>
