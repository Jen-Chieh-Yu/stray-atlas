/** Lucide icons (ISC License, https://lucide.dev), v1.43.0 as used in the
 *  drafts. Geometry is copied unmodified; see THIRD-PARTY-LICENSES.
 *
 *  Kept as data rather than as the lucide package: the site uses a dozen
 *  glyphs, and a table this size is easier to audit than a dependency.
 *
 *  Used by: LucideIcon.vue (draws the shapes) and AnimalCard.vue (the
 *  IconName type). Add a glyph here before using it anywhere. */
export type IconShape =
  | { d: string }
  | { cx: number; cy: number; r: number }
  | { x: number; y: number; width: number; height: number; rx: number }

export const ICONS = {
  menu: [{ d: 'M4 5h16' }, { d: 'M4 12h16' }, { d: 'M4 19h16' }],
  x: [{ d: 'M18 6 6 18' }, { d: 'm6 6 12 12' }],
  'chevron-down': [{ d: 'm6 9 6 6 6-6' }],
  'chevron-left': [{ d: 'm15 18-6-6 6-6' }],
  'chevron-right': [{ d: 'm9 18 6-6-6-6' }],
  'arrow-right': [{ d: 'M5 12h14' }, { d: 'm12 5 7 7-7 7' }],
  'arrow-up-down': [{ d: 'm21 16-4 4-4-4' }, { d: 'M17 20V4' }, { d: 'm3 8 4-4 4 4' }, { d: 'M7 4v16' }],
  'map-pin': [{ d: 'M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0' }, { cx: 12, cy: 10, r: 3 }],
  phone: [{ d: 'M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384' }],
  'external-link': [{ d: 'M15 3h6v6' }, { d: 'M10 14 21 3' }, { d: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6' }],
  hourglass: [
    { d: 'M5 22h14' },
    { d: 'M5 2h14' },
    { d: 'M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22' },
    { d: 'M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2' },
  ],
  'map-pinned': [
    { d: 'M18 8c0 3.613-3.869 7.429-5.393 8.795a1 1 0 0 1-1.214 0C9.87 15.429 6 11.613 6 8a6 6 0 0 1 12 0' },
    { cx: 12, cy: 8, r: 2 },
    { d: 'M8.714 14h-3.71a1 1 0 0 0-.948.683l-2.004 6A1 1 0 0 0 3 22h18a1 1 0 0 0 .948-1.316l-2-6a1 1 0 0 0-.949-.684h-3.712' },
  ],
  'chart-column': [{ d: 'M3 3v16a2 2 0 0 0 2 2h16' }, { d: 'M18 17V9' }, { d: 'M13 17V5' }, { d: 'M8 17v-3' }],
  list: [{ d: 'M3 5h.01' }, { d: 'M3 12h.01' }, { d: 'M3 19h.01' }, { d: 'M8 5h13' }, { d: 'M8 12h13' }, { d: 'M8 19h13' }],
  'layout-grid': [
    { x: 3, y: 3, width: 7, height: 7, rx: 1 },
    { x: 14, y: 3, width: 7, height: 7, rx: 1 },
    { x: 14, y: 14, width: 7, height: 7, rx: 1 },
    { x: 3, y: 14, width: 7, height: 7, rx: 1 },
  ],
  plus: [{ d: 'M5 12h14' }, { d: 'M12 5v14' }],
  search: [{ d: 'm21 21-4.34-4.34' }, { cx: 11, cy: 11, r: 8 }],
  clock: [{ cx: 12, cy: 12, r: 10 }, { d: 'M12 6v6l4 2' }],
  dog: [{ d: 'M11.25 16.25h1.5L12 17z' }, { d: 'M16 14v.5' }, { d: 'M4.42 11.247A13.152 13.152 0 0 0 4 14.556C4 18.728 7.582 21 12 21s8-2.272 8-6.444a11.702 11.702 0 0 0-.493-3.309' }, { d: 'M8 14v.5' }, { d: 'M8.5 8.5c-.384 1.05-1.083 2.028-2.344 2.5-1.931.722-3.576-.297-3.656-1-.113-.994 1.177-6.53 4-7 1.923-.321 3.651.845 3.651 2.235A7.497 7.497 0 0 1 14 5.277c0-1.39 1.844-2.598 3.767-2.277 2.823.47 4.113 6.006 4 7-.08.703-1.725 1.722-3.656 1-1.261-.472-1.855-1.45-2.239-2.5' }],
  cat: [{ d: 'M12 5c.67 0 1.35.09 2 .26 1.78-2 5.03-2.84 6.42-2.26 1.4.58-.42 7-.42 7 .57 1.07 1 2.24 1 3.44C21 17.9 16.97 21 12 21s-9-3-9-7.56c0-1.25.5-2.4 1-3.44 0 0-1.89-6.42-.5-7 1.39-.58 4.72.23 6.5 2.23A9.04 9.04 0 0 1 12 5Z' }, { d: 'M8 14v.5' }, { d: 'M16 14v.5' }, { d: 'M11.25 16.25h1.5L12 17l-.75-.75Z' }],
  mars: [{ d: 'M16 3h5v5' }, { d: 'm21 3-6.75 6.75' }, { cx: 10, cy: 14, r: 6 }],
  venus: [{ d: 'M12 15v7' }, { d: 'M9 19h6' }, { cx: 12, cy: 9, r: 6 }],
  'circle-help': [{ cx: 12, cy: 12, r: 10 }, { d: 'M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3' }, { d: 'M12 17h.01' }],
  'sliders-horizontal': [{ d: 'M10 5H3' }, { d: 'M12 19H3' }, { d: 'M14 3v4' }, { d: 'M16 17v4' }, { d: 'M21 12h-9' }, { d: 'M21 19h-5' }, { d: 'M21 5h-7' }, { d: 'M8 10v4' }, { d: 'M8 12H3' }],
} satisfies Record<string, IconShape[]>

export type IconName = keyof typeof ICONS
