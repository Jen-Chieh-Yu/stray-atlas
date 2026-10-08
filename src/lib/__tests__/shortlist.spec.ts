import { describe, expect, it } from 'vitest'
import { entryFor, entryLabel, groupByShelter, parseStored, shortlistText } from '@/lib/shortlist'
import type { ShortlistEntry } from '@/lib/shortlist'

// Real animals from the 2026-10-07 snapshot; 108696 had left the list by then.
const taipei = 'e32bd54eef'
const taoyuan = 'e1942dfc8c'

function entry(id: string, shelter: string, fields: Partial<ShortlistEntry> = {}): ShortlistEntry {
  return {
    id,
    subid: `S${id}`,
    kind: '狗',
    variety: '混種犬',
    sex: 'F',
    shelter,
    shelterName: shelter === taipei ? '臺北市動物之家' : '桃園市動物保護教育園區',
    photo: '',
    added: '2026-10-01',
    snapshot: '2026-10-01',
    ...fields,
  }
}

describe('entryFor', () => {
  it('keeps what the list needs once the animal has left the roster', () => {
    const animal = {
      id: '31212',
      subid: '103030912',
      kind: '狗' as const,
      variety: '混種犬',
      sex: 'F',
      shelter: taipei,
      photo: 'https://www.pet.gov.tw/upload/pic/1674175843656.png',
    }
    expect(entryFor(animal, '臺北市動物之家', '2026-10-07', '2026-10-07')).toEqual({
      ...animal,
      shelterName: '臺北市動物之家',
      added: '2026-10-07',
      snapshot: '2026-10-07',
    })
  })
})

describe('parseStored', () => {
  it('reads back what was written', () => {
    const list = [entry('31212', taipei), entry('106960', taoyuan, { kind: '貓' })]
    expect(parseStored(JSON.stringify(list))).toEqual(list)
  })

  it('drops what it cannot read instead of failing', () => {
    expect(parseStored(null)).toEqual([])
    expect(parseStored('{not json')).toEqual([])
    expect(parseStored('{"id":"1"}')).toEqual([])
    const good = entry('31212', taipei)
    const stored = [good, { ...good, id: '2', kind: '鳥' }, { id: '3' }, 'x', null]
    expect(parseStored(JSON.stringify(stored))).toEqual([good])
  })

  it('keeps an animal listed twice once', () => {
    const one = entry('31212', taipei)
    expect(parseStored(JSON.stringify([one, { ...one, added: '2026-10-07' }]))).toEqual([one])
  })
})

describe('groupByShelter', () => {
  const list = [
    entry('106960', taoyuan),
    entry('31212', taipei),
    entry('31230', taipei),
    entry('108696', taipei),
  ]

  it('puts the shelter with most animals first and keeps the order they were added', () => {
    const groups = groupByShelter(list, () => undefined)
    expect(groups.map((group) => group.shelter)).toEqual([taipei, taoyuan])
    expect(groups[0].entries.map((item) => item.id)).toEqual(['31212', '31230', '108696'])
  })

  it("prefers the shelter's current name to the stored one", () => {
    const groups = groupByShelter(list, (id) =>
      id === taipei ? '臺北市動物之家（新）' : undefined,
    )
    expect(groups[0].name).toBe('臺北市動物之家（新）')
    expect(groups[1].name).toBe('桃園市動物保護教育園區')
  })
})

describe('entryLabel', () => {
  it('names breed and sex, and leaves out an unrecorded sex', () => {
    expect(entryLabel({ variety: '混種犬', sex: 'M' })).toBe('混種犬 公')
    expect(entryLabel({ variety: '', sex: 'N' })).toBe('未填品種')
  })
})

describe('shortlistText', () => {
  it('groups the numbers by shelter with its phone, and marks one no longer listed', () => {
    const groups = groupByShelter(
      [entry('31212', taipei), entry('108696', taipei), entry('106960', taoyuan, { subid: '' })],
      () => undefined,
    )
    const text = shortlistText(
      groups,
      (id) => (id === taipei ? '(02)87913254' : undefined),
      (id) => id !== '108696',
      '2026-10-07',
    )
    expect(text).toBe(
      [
        'StrayAtlas 候選清單（2026-10-07 資料）',
        '',
        '臺北市動物之家 (02)87913254',
        '- S31212 混種犬 母',
        '- S108696 混種犬 母（不在目前名單）',
        '',
        '桃園市動物保護教育園區',
        '- 流水號 106960 混種犬 母',
      ].join('\n'),
    )
  })
})
