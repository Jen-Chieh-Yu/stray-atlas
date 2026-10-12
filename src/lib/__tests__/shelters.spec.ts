import { describe, expect, it } from 'vitest'
import { dialHref, infoIsStale, infoNeedsCall, phoneOf } from '@/lib/shelters'
import type { ShelterInfo } from '@/types'

// Noon in Taipei, so the Taipei date is the one written.
const at = (day: string) => new Date(`${day}T12:00:00+08:00`)

function info(fields: Partial<ShelterInfo> = {}): ShelterInfo {
  return {
    hours: '週二至週日 10:00–16:00',
    visit: 'unstated',
    sources: [{ url: 'https://example.gov.tw/', title: '公告' }],
    checked: '2026-10-12',
    ...fields,
  }
}

describe('dialHref', () => {
  it('dials the digits of a number written with brackets and dashes', () => {
    expect(dialHref('(02)87913254')).toBe('tel:0287913254')
    expect(dialHref('0972-821052')).toBe('tel:0972821052')
  })

  it('puts an extension after a pause', () => {
    expect(dialHref('(03)9602350 分機 620')).toBe('tel:039602350,620')
  })

  it('gives nothing for a bare area code', () => {
    expect(dialHref('(72)')).toBeNull()
    expect(phoneOf({ tel: '(09)' }).href).toBeNull()
  })
})

describe('infoIsStale', () => {
  it('turns after 180 days, counted in Taipei', () => {
    expect(infoIsStale(info(), at('2027-04-10'))).toBe(false)
    expect(infoIsStale(info(), at('2027-04-11'))).toBe(true)
  })
})

describe('infoNeedsCall', () => {
  it('sends the visitor to the shelter page when the hours are disputed, missing or old', () => {
    expect(infoNeedsCall(info(), at('2026-10-12'))).toBe(false)
    expect(infoNeedsCall(info({ caution: '官方公告不一致' }), at('2026-10-12'))).toBe(true)
    expect(infoNeedsCall(info({ hours: undefined, note: '查不到' }), at('2026-10-12'))).toBe(true)
    expect(infoNeedsCall(info(), at('2027-05-01'))).toBe(true)
  })

  it('says nothing for a shelter the file does not cover', () => {
    expect(infoNeedsCall(undefined)).toBe(false)
  })
})
