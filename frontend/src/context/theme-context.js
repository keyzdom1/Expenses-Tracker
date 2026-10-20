import { createContext, useContext } from 'react'

/**
 * Theme context and helpers.
 *
 * Kept in a non-component module so the provider file only exports a
 * component (React Fast Refresh friendly).
 */

export const THEME_STORAGE_KEY = 'theme'
export const THEME_OPTIONS = ['light', 'dark', 'system']

export const ThemeContext = createContext(null)

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used inside <ThemeProvider>')
  return context
}

/** Read a CSS custom property (used to give Recharts real colour values). */
export function getToken(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
