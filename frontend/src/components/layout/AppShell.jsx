import {
  ArrowLeftRight,
  CalendarClock,
  FileText,
  Landmark,
  LayoutDashboard,
  LogOut,
  Settings as SettingsIcon,
  Tags,
  Target,
  Wallet,
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '../../context/auth-context'
import ThemeSync from '../ThemeSync'
import NotificationBell from './NotificationBell'
import ThemeToggle from './ThemeToggle'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/transactions', label: 'Transactions', Icon: ArrowLeftRight },
  { to: '/accounts', label: 'Accounts', Icon: Landmark },
  { to: '/categories', label: 'Categories', Icon: Tags },
  { to: '/budgets', label: 'Budgets', Icon: Target },
  { to: '/recurring', label: 'Recurring', Icon: CalendarClock },
  { to: '/reports', label: 'Reports', Icon: FileText },
  { to: '/settings', label: 'Settings', Icon: SettingsIcon },
]

function navClass({ isActive }) {
  return [
    'flex shrink-0 items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'bg-primary/10 text-primary'
      : 'text-text-muted hover:bg-surface-raised hover:text-text',
  ].join(' ')
}

export default function AppShell() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* Reset the theme from the user's saved preference on every login. */}
      <ThemeSync />

      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-on-primary"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-20 border-b border-border bg-surface print:hidden">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-on-primary">
              <Wallet size={18} aria-hidden="true" />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold text-text">Expense Tracker</p>
              <p className="hidden text-[11px] text-text-muted sm:block">{user?.email}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <NotificationBell />
            <ThemeToggle />
            <button
              type="button"
              onClick={handleSignOut}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
            >
              <LogOut size={14} aria-hidden="true" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>

        <nav aria-label="Main" className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 pb-2 sm:px-6">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={navClass}>
              <Icon size={15} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8 print:max-w-none print:p-0"
      >
        <Outlet />
      </main>
    </div>
  )
}
