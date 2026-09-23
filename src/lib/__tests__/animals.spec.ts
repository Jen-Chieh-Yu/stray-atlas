import { describe, expect, it } from 'vitest'
import {
  animalsLink,
  DAY_BANDS,
  inBand,
  median,
  parseAnimalQuery,
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
