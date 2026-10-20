import { Wallet } from 'lucide-react'

import ThemeToggle from './ThemeToggle'

/** Centered layout shared by login, registration and password pages. */
export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <header className="flex items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-on-primary">
            <Wallet size={18} aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold text-text">Expense Tracker</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-12">
        <div className="w-full max-w-md">
          <div className="card p-6 sm:p-8">
            <h1 className="text-xl font-semibold tracking-tight text-text">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-text-muted">{subtitle}</p>}
            <div className="mt-6">{children}</div>
          </div>
          {footer && <div className="mt-4 text-center text-sm text-text-muted">{footer}</div>}
        </div>
      </main>

      <footer className="px-4 py-4 text-center text-[11px] text-text-muted">
        Your financial data is private and only visible to your account.
      </footer>
    </div>
  )
}
