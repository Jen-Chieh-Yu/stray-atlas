/** Lucide icons (ISC License, https://lucide.dev), v1.43.0 as used in the
 *  drafts. Geometry is copied unmodified; see THIRD-PARTY-LICENSES.
 *
 *  Kept as data rather than as the lucide package: the site uses a dozen
 *  glyphs, and a table this size is easier to audit than a dependency.
 *
 *  Used by: LucideIcon.vue (draws the shapes) and AnimalCard.vue (the
 *  IconName type). Add a glyph here before using it anywhere. */
export type IconShape = { d: string } | { cx: number; cy: number; r: number }

export const ICONS = {
  menu: [{ d: 'M4 5h16' }, { d: 'M4 12h16' }, { d: 'M4 19h16' }],
  x: [{ d: 'M18 6 6 18' }, { d: 'm6 6 12 12' }],
  'chevron-left': [{ d: 'm15 18-6-6 6-6' }],
  'chevron-right': [{ d: 'm9 18 6-6-6-6' }],
  'arrow-right': [{ d: 'M5 12h14' }, { d: 'm12 5 7 7-7 7' }],
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
