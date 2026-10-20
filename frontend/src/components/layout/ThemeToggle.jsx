import { Monitor, Moon, Sun } from 'lucide-react'

import { useTheme } from '../../context/theme-context'

const OPTIONS = [
  { value: 'light', label: 'Light', Icon: Sun },
  { value: 'dark', label: 'Dark', Icon: Moon },
  { value: 'system', label: 'System', Icon: Monitor },
]

/**
 * Light / Dark / System selector.
 *
 * Accessibility: it is a group of toggle buttons with aria-pressed, so the
 * active choice is announced to screen readers - colour is never the only cue.
 */
export default function ThemeToggle({ className = '' }) {
  const { theme, setTheme } = useTheme()

  return (
    <div
      role="group"
      aria-label="Colour theme"
      className={`inline-flex items-center gap-1 rounded-xl border border-border bg-surface-raised p-1 ${className}`}
    >
      {OPTIONS.map(({ value, label, Icon }) => {
        const active = theme === value
        return (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            aria-pressed={active}
            aria-label={`${label} theme`}
            title={`${label} theme`}
            className={[
              'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors',
              'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
              active
                ? 'bg-surface text-text shadow-sm ring-1 ring-border'
                : 'text-text-muted hover:bg-surface hover:text-text',
            ].join(' ')}
          >
            <Icon size={14} aria-hidden="true" />
            <span className="hidden sm:inline" aria-hidden="true">
              {label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
