import { describe, expect, it } from 'vitest'
import {
  DEFAULT_OG_IMAGE,
  dataCredit,
  shareDescription,
  shareMessage,
  sharePageHtml,
  shareTitle,
  shareUrl,
} from '@/lib/share'

// 468422 in the 2026-10-04 snapshot, the example in the drafts.
const bullTerrier = {
  id: '468422',
  subid: 'CAAAG1150917005',
  variety: '牛頭梗',
  sex: 'F',
  opendate: '2026-10-05',
  photo: 'https://www.pet.gov.tw/upload/pic/1789620234138.png',
}
const SHELTER = '桃園市動物保護教育園區'
const SNAPSHOT = '2026-10-04'

describe('shareUrl', () => {
  it('ends in a slash, so GitHub Pages serves it without a redirect', () => {
    expect(shareUrl('468422')).toBe('https://jen-chieh-yu.github.io/stray-atlas/a/468422/')
  })
})

describe('shareTitle', () => {
  it('names breed, sex and shelter', () => {
    expect(shareTitle(bullTerrier, SHELTER)).toBe('牛頭梗・母・桃園市動物保護教育園區')
  })

  it('leaves out an unrecorded sex and names a blank breed', () => {
    expect(shareTitle({ ...bullTerrier, variety: '', sex: 'N' }, SHELTER)).toBe(
      '未填品種・桃園市動物保護教育園區',
    )
  })
})

describe('shareDescription', () => {
  it('closes with the snapshot date, since a preview is cached', () => {
    expect(shareDescription(bullTerrier, 17, SNAPSHOT)).toBe(
      '收容編號 CAAAG1150917005・已在所 17 天・10/05 起開放認養（2026-10-04 資料）',
    )
  })

  it('names the opening day only while it is still ahead', () => {
    expect(shareDescription(bullTerrier, 17, '2026-10-05')).toBe(
      '收容編號 CAAAG1150917005・已在所 17 天（2026-10-05 資料）',
    )
  })

  it('skips what it does not know', () => {
    expect(shareDescription({ ...bullTerrier, subid: '', opendate: '' }, null, SNAPSHOT)).toBe(
      '（2026-10-04 資料）',
    )
  })

  it('groups thousands as the cards do', () => {
    expect(shareDescription({ ...bullTerrier, opendate: '' }, 4707, SNAPSHOT)).toContain(
      '已在所 4,707 天',
    )
  })
})

describe('shareMessage', () => {
  it('reads as the draft does, with the link apart', () => {
    expect(shareMessage(bullTerrier, SHELTER, 17, SNAPSHOT)).toEqual({
      text:
        '桃園市動物保護教育園區的牛頭梗（母），已在所 17 天，10/05 起開放認養。\n' +
        '收容編號 CAAAG1150917005（2026-10-04 資料）',
      url: 'https://jen-chieh-yu.github.io/stray-atlas/a/468422/',
    })
  })

  it('drops the parentheses for an unrecorded sex and copes without a shelter', () => {
    const { text } = shareMessage({ ...bullTerrier, sex: 'N', opendate: '' }, '', null, SNAPSHOT)
    expect(text).toBe('牛頭梗。\n收容編號 CAAAG1150917005（2026-10-04 資料）')
  })
})

describe('dataCredit', () => {
  it('follows the licence attachment, with the snapshot for a version', () => {
    expect(dataCredit(SNAPSHOT)).toMatch(/^農業部 2026 動物認領養（2026-10-04 快照）。此開放資料依/)
  })
})

describe('sharePageHtml', () => {
  const page = sharePageHtml(bullTerrier, SHELTER, 17, SNAPSHOT, '/stray-atlas/')

  it('previews the animal with its photo', () => {
    expect(page).toContain(
      '<meta property="og:title" content="牛頭梗・母・桃園市動物保護教育園區">',
    )
    expect(page).toContain(`<meta property="og:image" content="${bullTerrier.photo}">`)
    expect(page).toContain(
      '<meta property="og:url" content="https://jen-chieh-yu.github.io/stray-atlas/a/468422/">',
    )
  })

  it('falls back to the site image, with its size, when there is no photo', () => {
    const bare = sharePageHtml(
      { ...bullTerrier, photo: '' },
      SHELTER,
      17,
      SNAPSHOT,
      '/stray-atlas/',
    )
    expect(bare).toContain(`<meta property="og:image" content="${DEFAULT_OG_IMAGE}">`)
    expect(bare).toContain('<meta property="og:image:width" content="1200">')
  })

  it('sends a reader to the dialog by script, not by meta refresh', () => {
    expect(page).toContain(
      '<script>location.replace("/stray-atlas/animals?animal=468422")</script>',
    )
    expect(page).not.toContain('http-equiv')
    expect(page).toContain('<meta name="robots" content="noindex">')
  })

  it('credits the photos and the data', () => {
    expect(page).toContain('經全國動物收容資訊網（pet.gov.tw）公開')
    expect(page).toContain('政府資料開放授權條款')
  })

  it('escapes what comes from the source', () => {
    const odd = sharePageHtml(
      { ...bullTerrier, variety: '"><script>x</script>' },
      SHELTER,
      17,
      SNAPSHOT,
      '/stray-atlas/',
    )
    expect(odd).not.toContain('<script>x')
    expect(odd).toContain('&quot;&gt;&lt;script&gt;x&lt;/script&gt;')
  })
})
