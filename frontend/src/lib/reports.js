/**
 * Reporting date helpers shared by the dashboard and the reports page.
 * Values are calendar dates in the user's local timezone (YYYY-MM-DD).
 */

export const REPORT_PRESETS = [
  { key: 'month', label: 'This month' },
  { key: 'last', label: 'Last month' },
  { key: 'quarter', label: 'Last 3 months' },
  { key: 'year', label: 'This year' },
]

export function isoDate(value) {
  return [
    value.getFullYear(),
    String(value.getMonth() + 1).padStart(2, '0'),
    String(value.getDate()).padStart(2, '0'),
  ].join('-')
}

/** Add days to a YYYY-MM-DD string without timezone drift. */
export function addDaysISO(value, days) {
  const [year, month, day] = value.split('-').map(Number)
  return isoDate(new Date(year, month - 1, day + days))
}

export function rangeFor(key, now = new Date()) {
  const year = now.getFullYear()
  const month = now.getMonth()

  if (key === 'last') {
    return {
      dateFrom: isoDate(new Date(year, month - 1, 1)),
      dateTo: isoDate(new Date(year, month, 0)),
    }
  }
  if (key === 'quarter') {
    return { dateFrom: isoDate(new Date(year, month - 2, 1)), dateTo: isoDate(now) }
  }
  if (key === 'year') {
    return { dateFrom: isoDate(new Date(year, 0, 1)), dateTo: isoDate(now) }
  }
  return { dateFrom: isoDate(new Date(year, month, 1)), dateTo: isoDate(now) }
}

/** Read the filename the API suggests, falling back to a safe default. */
export function filenameFromDisposition(header, fallback = 'transactions.csv') {
  if (!header) return fallback

  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim())
    } catch {
      return fallback
    }
  }

  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain ? plain[1].trim() : fallback
}
