// ESLint checks logic; Prettier owns formatting (see .prettierrc).
//
// eslint-plugin-prettier is deliberately not used: running Prettier inside
// ESLint turns every formatting nit into a lint error and slows the editor.
// `npm run format:check` covers formatting separately.
import js from '@eslint/js'
import { vueTsConfigs, withVueTs } from '@vue/eslint-config-typescript'
import eslintConfigPrettier from 'eslint-config-prettier'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'

export default withVueTs(
  // Global ignores. An object with `ignores` and no other key applies to
  // every config below; add any other key and it only applies to itself.
  {
    ignores: [
      'dist/**',
      'coverage/**',
      // Generated JSON written by the Python pipeline, not code.
      'public/data/**',
      // Scratch prototypes and drafts, kept out of version control.
      '.notes/**',
      'tmp/**',
    ],
  },

  {
    linterOptions: {
      // A disable comment that no longer disables anything is a stale excuse.
      reportUnusedDisableDirectives: 'error',
    },
  },

  js.configs.recommended,
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,

  // The app runs in the browser.
  {
    files: ['src/**/*.{ts,vue}'],
    languageOptions: { globals: globals.browser },
  },

  // Build and tool configs run in Node.
  {
    files: ['*.{js,ts}'],
    languageOptions: { globals: globals.node },
  },

  // Turns off every rule that Prettier would fight with, including the
  // formatting rules eslint-plugin-vue enables. Must stay last.
  eslintConfigPrettier,
)
