import { useCallback, useEffect, useMemo, useState } from 'react'

import { THEME_OPTIONS, THEME_STORAGE_KEY, ThemeContext } from './theme-context'

function getSystemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Read the stored preference; an absent value means "follow the system". */
function readStoredTheme() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    return THEME_OPTIONS.includes(stored) ? stored : 'system'
  } catch {
    return 'system'
  }
}

function applyThemeClass(dark) {
  document.documentElement.classList.toggle('dark', dark)
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', dark ? '#0B1220' : '#F8FAFC')
}

export default function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readStoredTheme)
  const [systemPrefersDark, setSystemPrefersDark] = useState(getSystemPrefersDark)

  // Keep the OS preference in sync while the user has "System" selected.
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (event) => setSystemPrefersDark(event.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  const resolvedTheme = theme === 'system' ? (systemPrefersDark ? 'dark' : 'light') : theme

  // Apply the class whenever the resolved theme changes.
  useEffect(() => {
    applyThemeClass(resolvedTheme === 'dark')
  }, [resolvedTheme])

  /** Change theme, persist locally, and (from Phase 2) sync to the profile. */
  const setTheme = useCallback((next) => {
    if (!THEME_OPTIONS.includes(next)) return
    setThemeState(next)
    try {
      if (next === 'system') localStorage.removeItem(THEME_STORAGE_KEY)
      else localStorage.setItem(THEME_STORAGE_KEY, next)
    } catch {
      /* storage unavailable - the in-memory choice still applies */
    }
    // TODO(Phase 2): PATCH /api/v1/me/preferences { theme: next } once auth exists.
  }, [])

  /** Cycle Light -> Dark -> System, available for a compact mobile control. */
  const cycleTheme = useCallback(() => {
    const order = ['light', 'dark', 'system']
    setTheme(order[(order.indexOf(theme) + 1) % order.length])
  }, [theme, setTheme])

  const value = useMemo(
    () => ({ theme, resolvedTheme, isDark: resolvedTheme === 'dark', setTheme, cycleTheme }),
    [theme, resolvedTheme, setTheme, cycleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
