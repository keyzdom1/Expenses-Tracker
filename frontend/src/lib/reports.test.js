import { describe, expect, it } from 'vitest'

import { addDaysISO, filenameFromDisposition, isoDate, rangeFor } from './reports'

describe('isoDate', () => {
  it('formats a local date without shifting timezones', () => {
    expect(isoDate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })
})

describe('addDaysISO', () => {
  it('crosses month boundaries using calendar days', () => {
    expect(addDaysISO('2026-01-31', 1)).toBe('2026-02-01')
    expect(addDaysISO('2026-12-31', 1)).toBe('2027-01-01')
  })
})

describe('rangeFor', () => {
  const now = new Date(2026, 0, 15) // 15 January 2026

  it('defaults to the current month', () => {
    expect(rangeFor('month', now)).toEqual({ dateFrom: '2026-01-01', dateTo: '2026-01-15' })
  })

  it('covers the whole previous month', () => {
    expect(rangeFor('last', now)).toEqual({ dateFrom: '2025-12-01', dateTo: '2025-12-31' })
  })

  it('covers three months including the current one', () => {
    expect(rangeFor('quarter', now)).toEqual({ dateFrom: '2025-11-01', dateTo: '2026-01-15' })
  })

  it('covers the year to date', () => {
    expect(rangeFor('year', now)).toEqual({ dateFrom: '2026-01-01', dateTo: '2026-01-15' })
  })
})

describe('filenameFromDisposition', () => {
  it('reads a quoted filename', () => {
    expect(
      filenameFromDisposition('attachment; filename="transactions-2026-01-01-to-2026-01-31.csv"'),
    ).toBe('transactions-2026-01-01-to-2026-01-31.csv')
  })

  it('reads an encoded filename', () => {
    expect(filenameFromDisposition("attachment; filename*=UTF-8''report%20jan.csv")).toBe(
      'report jan.csv',
    )
  })

  it('falls back when the header is missing', () => {
    expect(filenameFromDisposition(undefined)).toBe('transactions.csv')
    expect(filenameFromDisposition('attachment')).toBe('transactions.csv')
  })
})
