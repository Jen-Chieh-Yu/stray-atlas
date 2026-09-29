<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

/** The frame both animal dialogs sit in: backdrop, sticky top bar with a
 *  close button, Esc, focus and the scroll lock. What goes in the bar and
 *  below it is the caller's (DESIGN.md §10).
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
  () => props.resetKey,
  () => {
    if (panel.value) panel.value.scrollTop = 0
    panel.value?.focus()
  },
)
</script>

<template>
  <Teleport to="body">
    <div class="backdrop" @click.self="emit('close')">
      <div ref="panel" class="dialog" role="dialog" aria-modal="true" :aria-label="label" tabindex="-1">
        <header class="bar">
          <slot name="bar" />
          <button type="button" class="close" aria-label="關閉" @click="emit('close')">×</button>
        </header>
        <slot />
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
