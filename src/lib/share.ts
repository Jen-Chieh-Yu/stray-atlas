import { SEX_LABEL, formatCount, monthDay, opensAfter } from './animals'
import type { Animal } from '../types'

/* Sharing one animal: the words a visitor sends, and the small page a chat
 * app or social site reads to draw the link's preview.
 *
 * A link preview is read from the page's HTML by a crawler that runs no
 * JavaScript, so /animals?animal=<id> can only ever show the site's own
 * title. The build writes /a/<id>/index.html for every animal instead (see
 * sharePages() in vite.config.ts): the preview tags for that animal, then a
 * script that sends a reader on to the dialog. An animal that has left the
 * list loses its page on the next deploy, and the link falls through
 * 404.html to the router, which opens the 不在目前名單 dialog.
 *
 * Relative imports only: vite.config.ts loads this file at build time,
 * outside the app's @ alias.
 *
 * Used by: AnimalDialog.vue (shareUrl, shareMessage) and vite.config.ts
 * (sharePageHtml).
 */

/** Where the site is served. Previews need absolute URLs, and a share copied
 *  from `npm run dev` should still point at the real site. */
export const SITE_URL = 'https://jen-chieh-yu.github.io/stray-atlas/'

/** The preview image for an animal without a photo, and for every other page.
 *  Drawn without any figure that changes, since it is never redrawn. */
export const DEFAULT_OG_IMAGE = `${SITE_URL}og.png`

/** The photos are the shelters'; the site links to them where they are
 *  published and keeps no copy. Chosen 2026-10-07, with the licence for the
 *  photos themselves unstated by the source (DESIGN.md §10). */
export const PHOTO_CREDIT =
  '動物照片由各公立動物收容所拍攝登錄，經全國動物收容資訊網（pet.gov.tw）公開；本站僅以原網址連結顯示。'

/** The attribution the Open Government Data License asks for (its attachment,
 *  顯名聲明). The dataset states no version number, so the snapshot date
 *  stands in for it. */
export function dataCredit(snapshotDate: string): string {
  return (
    `農業部 ${snapshotDate.slice(0, 4)} 動物認領養（${snapshotDate} 快照）。` +
    '此開放資料依政府資料開放授權條款 (Open Government Data License) 進行公眾釋出，' +
    '使用者於遵守本條款各項規定之前提下，得利用之。'
  )
}

/** With the trailing slash GitHub Pages would otherwise redirect to. */
export function shareUrl(id: string): string {
  return `${SITE_URL}a/${encodeURIComponent(id)}/`
}

type Shared = Pick<Animal, 'id' | 'subid' | 'variety' | 'sex' | 'opendate'>

/** Only 公 and 母 say anything; 未填 is left out rather than printed. */
function sexWord(sex: string): string {
  return sex === 'M' || sex === 'F' ? SEX_LABEL[sex] : ''
}

function opensText(animal: Shared, snapshotDate: string): string {
  return opensAfter(animal.opendate, snapshotDate) ? `${monthDay(animal.opendate)} 起開放認養` : ''
}

/** 牛頭梗・母・桃園市動物保護教育園區 */
export function shareTitle(animal: Shared, shelterName: string): string {
  return [animal.variety || '未填品種', sexWord(animal.sex), shelterName].filter(Boolean).join('・')
}

/** 收容編號 X・已在所 17 天・10/05 起開放認養（2026-10-04 資料）
 *
 *  The date closes it because a preview is cached by the app that drew it and
 *  never updates: the reader has to be able to tell how old it is. */
export function shareDescription(
  animal: Shared,
  days: number | null,
  snapshotDate: string,
): string {
  const parts = [
    animal.subid ? `收容編號 ${animal.subid}` : '',
    days === null ? '' : `已在所 ${formatCount(days)} 天`,
    opensText(animal, snapshotDate),
  ].filter(Boolean)
  return `${parts.join('・')}（${snapshotDate} 資料）`
}

/** What 分享 and 複製介紹與連結 hand over, the link on a line of its own so
 *  a chat app turns it into a preview. Facts only: no 快來認養 or 急需, which
 *  the site does not say anywhere (DESIGN.md §12.6). */
export function shareMessage(
  animal: Shared,
  shelterName: string,
  days: number | null,
  snapshotDate: string,
): { text: string; url: string } {
  const sex = sexWord(animal.sex)
  const who = `${animal.variety || '未填品種'}${sex ? `（${sex}）` : ''}`
  const first = [
    shelterName ? `${shelterName}的${who}` : who,
    days === null ? '' : `已在所 ${formatCount(days)} 天`,
    opensText(animal, snapshotDate),
  ]
    .filter(Boolean)
    .join('，')
  const second = animal.subid
    ? `收容編號 ${animal.subid}（${snapshotDate} 資料）`
    : `（${snapshotDate} 資料）`
  return { text: `${first}。\n${second}`, url: shareUrl(animal.id) }
}

const ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ESCAPES[char] ?? char)
}

/** The page at /a/<id>/: preview tags for crawlers, a script that moves a
 *  reader on to the dialog at once, and the credits for anyone who reads the
 *  source. `noindex` keeps 8,000 thin pages out of search results; it does
 *  not stop a chat app from drawing the preview.
 *
 *  No meta refresh: some crawlers follow it, and would then describe the
 *  page it lands on instead of this one. */
export function sharePageHtml(
  animal: Shared & Pick<Animal, 'photo'>,
  shelterName: string,
  days: number | null,
  snapshotDate: string,
  basePath: string,
): string {
  const title = shareTitle(animal, shelterName)
  const description = shareDescription(animal, days, snapshotDate)
  const target = `${basePath}animals?animal=${encodeURIComponent(animal.id)}`
  const image = animal.photo
    ? [
        ['og:image', animal.photo],
        ['og:image:alt', `${title} 的照片`],
      ]
    : [
        ['og:image', DEFAULT_OG_IMAGE],
        ['og:image:width', '1200'],
        ['og:image:height', '630'],
        ['og:image:alt', 'StrayAtlas 浪浪地圖'],
      ]
  const meta = [
    ['og:type', 'website'],
    ['og:site_name', 'StrayAtlas 浪浪地圖'],
    ['og:locale', 'zh_TW'],
    ['og:title', title],
    ['og:description', description],
    ['og:url', shareUrl(animal.id)],
    ...image,
  ]
    .map(([property, content]) => `<meta property="${property}" content="${escapeHtml(content)}">`)
    .join('\n')
  // JSON, not a bare string, so no value can close the script early.
  const script = JSON.stringify(target).replace(/</g, '\\u003c')
  return `<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}｜StrayAtlas 浪浪地圖</title>
<meta name="description" content="${escapeHtml(description)}">
<meta name="robots" content="noindex">
${meta}
<meta name="twitter:card" content="summary_large_image">
<script>location.replace(${script})</script>
</head>
<body>
<p><a href="${escapeHtml(target)}">到 StrayAtlas 浪浪地圖看這隻動物</a></p>
<p>${escapeHtml(PHOTO_CREDIT)}</p>
<p>${escapeHtml(dataCredit(snapshotDate))}</p>
</body>
</html>
`
}
