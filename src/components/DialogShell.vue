<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

/** The frame both animal dialogs sit in: backdrop, sticky top bar with a
 *  close button, Esc, focus, the scroll lock and the fade in and out. What
 *  goes in the bar and below it is the caller's (DESIGN.md §10).
 *
 *  Used by: AnimalDialog.vue and MissingAnimalDialog.vue. */
const props = defineProps<{
  label: string
  /** Changing it scrolls the panel back to the top, for when the dialog
   *  stays open but shows another animal. */
  resetKey?: string
}>()
const emit = defineEmits<{ close: [] }>()

const panel = ref<HTMLElement | null>(null)

/* ── Closing ───────────────────────────────────────────────────────────────
 * A <Transition> that is itself being removed skips its leave, so when the
 * caller's v-if takes the dialog away there is no fade. Closing from inside
 * therefore fades first and tells the caller afterwards: Esc, the backdrop
 * and × come here, and the dialogs' own 關閉 buttons call close() through a
 * template ref. Leaving by the browser's Back still closes at once. */

const shown = ref(true)

function close() {
  shown.value = false
}

defineExpose({ close })

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
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
  () => props.resetKey,
  () => {
    if (panel.value) panel.value.scrollTop = 0
    panel.value?.focus()
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="shell" appear @after-leave="emit('close')">
      <div v-if="shown" class="backdrop" @click.self="close">
        <div
          ref="panel"
          class="dialog"
          role="dialog"
          aria-modal="true"
          :aria-label="label"
          tabindex="-1"
        >
          <header class="bar">
            <slot name="bar" />
            <button type="button" class="close" aria-label="關閉" @click="close">×</button>
          </header>
          <slot />
        </div>
      </div>
    </Transition>
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

/* Fades in and out (DESIGN.md §10), the panel growing from 96% as it comes.
   Showing another animal keeps the frame, so nothing replays. */
.shell-enter-active {
  transition: opacity 200ms ease-out;

  & .dialog {
    transition: transform 200ms ease-out;
  }
}

.shell-leave-active {
  transition: opacity 160ms ease-in;

  & .dialog {
    transition: transform 160ms ease-in;
  }
}

.shell-enter-from,
.shell-leave-to {
  opacity: 0;

  & .dialog {
    transform: scale(0.96);
  }
}

@media (prefers-reduced-motion: reduce) {
  .shell-enter-active,
  .shell-leave-active,
  .shell-enter-active .dialog,
  .shell-leave-active .dialog {
    transition: none;
  }
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

  &:hover {
    background: var(--surface-sunk);
    color: var(--ink);
  }
}
</style>
