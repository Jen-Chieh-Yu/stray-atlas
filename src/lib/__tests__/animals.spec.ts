import { describe, expect, it } from 'vitest'
import {
  animalsLink,
  DAY_BANDS,
  inBand,
  isIdQuery,
  isNewerId,
  matchesId,
  median,
  monthDay,
  monthDayLong,
  opensAfter,
  parseAnimalQuery,
  pickSiblings,
  rank,
  rosterHint,
  searchLink,
  sumCounts,
  tally,
} from '@/lib/animals'

/* The /animals query contract, and the helpers every page shares.
 *
 * DESIGN.md §4: the URL is the state. A shared link, a refresh and the back
 * button all have to land on the same screen, which makes the parser the one
 * piece of frontend logic that other people's links depend on.
 */

describe('inBand', () => {
  it('excludes an animal with no recorded duration', () => {
    expect(inBand(null, 0, 30)).toBe(false)
  })

  it('includes both ends of a closed band', () => {
    expect(inBand(0, 0, 30)).toBe(true)
    expect(inBand(30, 0, 30)).toBe(true)
    expect(inBand(31, 0, 30)).toBe(false)
  })

  it('treats a null upper bound as open-ended', () => {
    expect(inBand(10_000, 1826, null)).toBe(true)
  })

  it('covers every day with exactly one band', () => {
    // A gap would hide animals from every filter at once; an overlap would
    // count one animal twice in the counts beside the chips.
    for (const days of [0, 30, 31, 90, 91, 365, 366, 730, 731, 1825, 1826, 5000]) {
      const matches = DAY_BANDS.filter((band) => inBand(days, band.min, band.max))
      expect(matches.length, `${days} days`).toBe(1)
    }
  })
})

describe('parseAnimalQuery', () => {
  it('reads the documented parameters', () => {
    const query = parseAnimalQuery({ kind: 'cat', county: '臺北市', sort: 'shortest' })
    expect(query.kind).toBe('貓')
    expect(query.county).toBe('臺北市')
    expect(query.sort).toBe('shortest')
  })

  it('drops a value the page cannot use rather than guessing', () => {
    // A stale link should show more animals, never the wrong ones.
    const query = parseAnimalQuery({ kind: 'bird', sex: 'Z', body: 'HUGE', age: 'OLD' })
    expect(query.kind).toBeUndefined()
    expect(query.sex).toBeUndefined()
    expect(query.body).toBeUndefined()
    expect(query.age).toBeUndefined()
  })

  it('lets the exact band win over the lower bound', () => {
    // They are one control in the UI; honouring both would filter twice.
    const query = parseAnimalQuery({ days: '1-2y', daysFrom: '5y+' })
    expect(query.days).toBe('1-2y')
    expect(query.daysFrom).toBeUndefined()
  })

  it('falls back to the lower bound when the band is unknown', () => {
    const query = parseAnimalQuery({ days: 'last-tuesday', daysFrom: '2-5y' })
    expect(query.days).toBeUndefined()
    expect(query.daysFrom).toBe('2-5y')
  })

  it('treats a whitespace-only search as no search', () => {
    expect(parseAnimalQuery({ q: '   ' }).q).toBeUndefined()
    expect(parseAnimalQuery({ q: '  米克斯 ' }).q).toBe('米克斯')
  })

  it('keeps only the non-default sort', () => {
    // 'longest' is the default, so it never needs to be in the URL.
    expect(parseAnimalQuery({ sort: 'longest' }).sort).toBeUndefined()
  })

  it('takes the first value when a key is repeated', () => {
    expect(parseAnimalQuery({ kind: ['dog', 'cat'] }).kind).toBe('狗')
  })

  it('ignores an empty value', () => {
    expect(parseAnimalQuery({ county: '' }).county).toBeUndefined()
  })
})

describe('animalsLink', () => {
  it('writes the kind in its URL form', () => {
    expect(animalsLink({ kind: '貓' })).toEqual({ path: '/animals', query: { kind: 'cat' } })
  })

  it('leaves absent filters out of the query', () => {
    const link = animalsLink({ kind: '狗', county: undefined, q: '' })
    expect(link.query).toEqual({ kind: 'dog' })
  })

  it('round-trips through the parser', () => {
    // The home page builds links with this and /animals reads them with the
    // parser; the two must agree or a chip lands on the wrong filter.
    const source = { kind: '貓' as const, county: '雲林縣', days: '2-5y' as const }
    expect(parseAnimalQuery(animalsLink(source).query)).toMatchObject(source)
  })
})

describe('isIdQuery', () => {
  it('recognises the shelters’ different numbering schemes', () => {
    // Formats seen in the 2026-09-29 snapshot.
    for (const id of ['AAAHG1141003002', 'W150910-14', '107-E015D', '1141317', '415705']) {
      expect(isIdQuery(id), id).toBe(true)
    }
  })

  it('leaves place and breed searches to the text matcher', () => {
    expect(isIdQuery('臺北市')).toBe(false)
    expect(isIdQuery('米克斯')).toBe(false)
    expect(isIdQuery('柴犬')).toBe(false)
  })

  it('needs a digit, and no Han character or space', () => {
    expect(isIdQuery('abc')).toBe(false)
    expect(isIdQuery('第2區')).toBe(false)
    expect(isIdQuery('AAAHG 1141003002')).toBe(false)
    expect(isIdQuery(undefined)).toBe(false)
  })
})

describe('matchesId', () => {
  const animal = { id: '424951', subid: 'AAAHG1141003002' }

  it('matches either number, ignoring case', () => {
    expect(matchesId(animal, 'aaahg1141003002')).toBe(true)
    expect(matchesId(animal, '424951')).toBe(true)
  })

  it('never matches a fragment', () => {
    // A fragment hits hundreds of animals and finds none of them.
    expect(matchesId(animal, '1141003')).toBe(false)
    expect(matchesId(animal, '42495')).toBe(false)
  })
})

describe('searchLink', () => {
  const roster = [
    { id: '1', subid: 'A100' },
    { id: '2', subid: 'B200' },
    { id: '3', subid: 'B200' },
  ]

  it('opens the one animal a number points to, dropping every other filter', () => {
    const link = searchLink(' a100 ', { kind: '狗', county: '臺北市' }, roster)
    expect(link).toEqual({ path: '/animals', query: { q: 'a100', animal: '1' } })
  })

  it('lists every animal a duplicated number points to', () => {
    expect(searchLink('B200', { kind: '貓' }, roster).query).toEqual({ q: 'B200' })
  })

  it('keeps the filters for a text search', () => {
    expect(searchLink('米克斯', { kind: '貓' }, roster).query).toEqual({ kind: 'cat', q: '米克斯' })
  })

  it('drops the search when the box is emptied', () => {
    expect(searchLink('  ', { kind: '貓' }, roster).query).toEqual({ kind: 'cat' })
  })
})

describe('isNewerId', () => {
  const roster = [{ id: '469480' }, { id: '35558' }]

  it('flags a 流水號 above every one in the roster', () => {
    expect(isNewerId('470102', roster)).toBe(true)
    expect(isNewerId('415705', roster)).toBe(false)
  })

  it('says nothing about 收容編號, which are not sequential', () => {
    expect(isNewerId('W990101-01', roster)).toBe(false)
  })

  it('says nothing against an empty roster', () => {
    expect(isNewerId('1', [])).toBe(false)
  })
})

describe('pickSiblings', () => {
  const pool = [
    { id: 'a', photo: '' },
    { id: 'b', photo: 'b.jpg' },
    { id: 'c', photo: 'c.jpg' },
    { id: 'd', photo: '' },
    { id: 'e', photo: 'e.jpg' },
  ]

  it('puts animals with a photo first and fills up with the rest', () => {
    const picked = pickSiblings(pool, 4, () => 0.5)
    expect(picked).toHaveLength(4)
    expect(picked.slice(0, 3).every((animal) => animal.photo)).toBe(true)
    expect(picked[3].photo).toBe('')
  })

  it('returns fewer when the pool is short', () => {
    expect(pickSiblings(pool.slice(0, 2), 4)).toHaveLength(2)
  })

  it('depends on the random source, so each opening can differ', () => {
    const first = pickSiblings(pool, 2, () => 0.5).map((animal) => animal.id)
    const last = pickSiblings(pool, 2, () => 0.99).map((animal) => animal.id)
    expect(first).not.toEqual(last)
  })

  it('does not reorder the caller’s array', () => {
    const copy = [...pool]
    pickSiblings(pool, 4)
    expect(pool).toEqual(copy)
  })
})

describe('median', () => {
  it('has no median for an empty list', () => {
    expect(median([])).toBeNull()
  })

  it('takes the middle of an odd-length list', () => {
    expect(median([3, 1, 2])).toBe(2)
  })

  it('rounds the midpoint of an even-length list to a whole day', () => {
    expect(median([1, 2, 3, 4])).toBe(3)
  })

  it('does not reorder the caller’s array', () => {
    const values = [3, 1, 2]
    median(values)
    expect(values).toEqual([3, 1, 2])
  })
})

describe('tally', () => {
  it('counts by key, largest first', () => {
    const counts = tally(['a', 'b', 'a'], (item) => item)
    expect(counts[0]).toEqual(['a', 2])
  })

  it('breaks ties by name so the order is stable between renders', () => {
    const counts = tally(['貓', '狗'], (item) => item)
    expect(counts.map(([name]) => name)).toEqual(['狗', '貓'])
  })
})

describe('opensAfter', () => {
  it('flags an adoption date after the snapshot', () => {
    expect(opensAfter('2026-10-05', '2026-10-01')).toBe(true)
  })

  it('treats the snapshot day itself as already open', () => {
    expect(opensAfter('2026-10-01', '2026-10-01')).toBe(false)
    expect(opensAfter('2026-09-30', '2026-10-01')).toBe(false)
  })

  it('says nothing about a blank or malformed date', () => {
    // 1900-01-01 sentinels are already nulled to '' by the cleaner.
    expect(opensAfter('', '2026-10-01')).toBe(false)
    expect(opensAfter('2026/10/05', '2026-10-01')).toBe(false)
    expect(opensAfter('2026-10-05', '')).toBe(false)
  })
})

describe('monthDay and monthDayLong', () => {
  it('write the date the way the card and the dialog say it', () => {
    expect(monthDay('2026-10-05')).toBe('10/05')
    expect(monthDayLong('2026-10-05')).toBe('10 月 5 日')
  })
})

describe('rosterHint', () => {
  it('states how many animals are loading', () => {
    expect(rosterHint({ count: 8459 })).toBe('全國 8,459 隻動物的資料')
  })

  it('leaves the figures out when home.json is not there', () => {
    expect(rosterHint()).toBe('全國動物資料')
  })
})

describe('sumCounts', () => {
  it('adds the same key across tables, keeping first-seen order', () => {
    // The home page adds home.json's per-kind tables into all-kinds counts.
    const counts = sumCounts([
      ['雲林縣', 2],
      ['臺南市', 1],
      ['雲林縣', 3],
    ])
    expect([...counts]).toEqual([
      ['雲林縣', 5],
      ['臺南市', 1],
    ])
  })
})

describe('rank', () => {
  it('orders counts made elsewhere exactly as tally orders its own', () => {
    // home.json carries counts, not an order; the page must rank them the
    // way it ranked the roster before, or ties would swap places.
    const items = ['貓', '狗', '兔', '狗']
    expect(rank(Object.entries({ 貓: 1, 狗: 2, 兔: 1 }))).toEqual(tally(items, (item) => item))
  })
})
