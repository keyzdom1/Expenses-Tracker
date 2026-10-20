/**
 * Money and date helpers.
 *
 * Amounts are always integer minor units in storage and on the wire. The UI
 * only converts to major units for display and for text inputs.
 */

const MAX_SAFE_MINOR = Number.MAX_SAFE_INTEGER

export function formatMoney(minor, currency = 'NGN', decimalPlaces = 2) {
  const value = (minor ?? 0) / 10 ** decimalPlaces
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  }).format(value)
}

/** Format without the currency symbol (for tight table cells). */
export function formatAmount(minor, decimalPlaces = 2) {
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  }).format((minor ?? 0) / 10 ** decimalPlaces)
}

/**
 * Parse a user-entered amount into integer minor units without floats.
 * Returns null when the text is not a valid non-negative amount for the
 * currency's precision.
 */
export function parseAmountInput(input, decimalPlaces = 2) {
  const text = String(input ?? '')
    .trim()
    .replace(/,/g, '')
  if (!text) return null

  const pattern = decimalPlaces > 0 ? new RegExp(`^\\d+(\\.\\d{0,${decimalPlaces}})?$`) : /^\d+$/
  if (!pattern.test(text)) return null

  const [whole, fraction = ''] = text.split('.')
  const padded = (fraction + '0'.repeat(decimalPlaces)).slice(0, decimalPlaces)
  const minor = Number(whole) * 10 ** decimalPlaces + Number(padded || 0)
  return Number.isSafeInteger(minor) && Math.abs(minor) <= MAX_SAFE_MINOR ? minor : null
}

/** Like parseAmountInput, but accepts a leading minus (opening balances). */
export function parseSignedAmountInput(input, decimalPlaces = 2) {
  const text = String(input ?? '').trim()
  const negative = text.startsWith('-')
  const minor = parseAmountInput(negative ? text.slice(1) : text, decimalPlaces)
  if (minor === null) return null
  return negative ? -minor : minor
}

/** Render minor units for an editable text input. */
export function minorToInput(minor, decimalPlaces = 2) {
  if (minor === null || minor === undefined) return ''
  const negative = minor < 0
  const absolute = Math.abs(minor)
  const whole = Math.floor(absolute / 10 ** decimalPlaces)
  if (decimalPlaces === 0) return `${negative ? '-' : ''}${whole}`
  const fraction = String(absolute % 10 ** decimalPlaces).padStart(decimalPlaces, '0')
  return `${negative ? '-' : ''}${whole}.${fraction}`
}

/** Today in the user's local timezone, formatted as YYYY-MM-DD. */
export function todayISO() {
  const now = new Date()
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('-')
}

/** Format a date-only string without shifting it across timezones. */
export function formatDate(isoDate) {
  if (!isoDate) return ''
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Intl.DateTimeFormat(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(year, month - 1, day))
}

export function formatMonth(date) {
  return new Intl.DateTimeFormat(undefined, { month: 'short', year: 'numeric' }).format(date)
}

/** Format a UTC timestamp for notifications and other event feeds. */
export function formatDateTime(isoString) {
  if (!isoString) return ''
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(isoString))
}

export function titleCase(value) {
  return String(value ?? '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}
