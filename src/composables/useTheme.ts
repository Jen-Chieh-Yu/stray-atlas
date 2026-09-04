import { ref, watchEffect } from 'vue'

export type ThemeChoice = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'stray-atlas:theme'

function read(): ThemeChoice {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch {
    // Private windows and blocked site data throw on access rather than
    // returning null. Falling back to the system setting is the right answer.
  }
  return 'system'
}

const choice = ref<ThemeChoice>(read())

/** The stylesheet reads data-theme off <html>.
 *
 * 'system' removes the attribute so the prefers-color-scheme media query
 * takes over; an explicit choice stamps the attribute, which is written to win
 * over the media query in both directions.
 */
watchEffect(() => {
  const root = document.documentElement
  if (choice.value === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', choice.value)
  }
  try {
    localStorage.setItem(STORAGE_KEY, choice.value)
  } catch {
    // Not being able to remember the choice is not a reason to break the page.
  }
})

export function useTheme() {
  return { choice }
}
