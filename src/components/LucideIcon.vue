<script setup lang="ts">
import { ICONS } from '@/lib/icons'
import type { IconName } from '@/lib/icons'

/** Decorative by default. Pass `label` only where the icon is the sole carrier
 *  of meaning (the sex glyph on a card), and it becomes an img with that name.
 *
 *  Used by: App.vue, HomeView.vue, AnimalsView.vue and AnimalCard.vue. */
const props = withDefaults(defineProps<{ name: IconName; size?: number; label?: string }>(), {
  size: 18,
  label: undefined,
})
</script>

<template>
  <svg
    :class="['lucide', `lucide-${props.name}`]"
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :role="props.label ? 'img' : undefined"
    :aria-label="props.label"
    :aria-hidden="props.label ? undefined : 'true'"
  >
    <template v-for="(shape, index) in ICONS[props.name]" :key="index">
      <path v-if="'d' in shape" :d="shape.d" />
      <circle v-else :cx="shape.cx" :cy="shape.cy" :r="shape.r" />
    </template>
  </svg>
</template>
