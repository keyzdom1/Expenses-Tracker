import { describe, expect, it } from 'vitest'

import {
  formatDate,
  formatMoney,
  minorToInput,
  parseAmountInput,
  parseSignedAmountInput,
} from './format'

describe('money parsing', () => {
  it('converts major units to integer minor units without floats', () => {
    expect(parseAmountInput('1234.56', 2)).toBe(123456)
    expect(parseAmountInput('1,234.5', 2)).toBe(123450)
    expect(parseAmountInput('0.01', 2)).toBe(1)
    expect(parseAmountInput('10', 0)).toBe(10)
    expect(parseAmountInput('10.5', 0)).toBeNull()
  })

  it('rejects malformed or over-precise input', () => {
    expect(parseAmountInput('', 2)).toBeNull()
    expect(parseAmountInput('abc', 2)).toBeNull()
    expect(parseAmountInput('1.234', 2)).toBeNull()
    expect(parseAmountInput('-5', 2)).toBeNull()
    expect(parseAmountInput('1.2.3', 2)).toBeNull()
  })

  it('round-trips minor units through editable text', () => {
    expect(minorToInput(123456, 2)).toBe('1234.56')
    expect(minorToInput(5, 2)).toBe('0.05')
    expect(minorToInput(-2500, 2)).toBe('-25.00')
    expect(minorToInput(10, 0)).toBe('10')
  })

  it('accepts a leading minus only for signed amounts', () => {
    expect(parseSignedAmountInput('-25.50', 2)).toBe(-2550)
    expect(parseSignedAmountInput('25.50', 2)).toBe(2550)
    expect(parseSignedAmountInput('-', 2)).toBeNull()
    expect(parseSignedAmountInput('--5', 2)).toBeNull()
  })
})

describe('display helpers', () => {
  it('formats minor units with the currency', () => {
    const formatted = formatMoney(123456, 'NGN', 2)
    expect(formatted).toContain('1,234.56')
  })

  it('formats date-only values without shifting the day', () => {
    const formatted = formatDate('2026-01-01')
    expect(formatted).toContain('2026')
    expect(formatted).toContain('01')
  })
})
