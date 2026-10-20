import { useQuery } from '@tanstack/react-query'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowRight,
  ArrowUpRight,
  Landmark,
  PiggyBank,
  Plus,
  Target,
  Undo2,
  Wallet,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { CategoryChart, TrendChart } from '../components/dashboard/FinanceCharts'
import Alert from '../components/ui/Alert'
import { useBudgets, useBills, useCurrencies } from '../hooks/useReferenceData'
import { api, apiErrorMessage } from '../lib/api'
import { formatDate, formatMoney, titleCase, todayISO } from '../lib/format'
import { addDaysISO, rangeFor } from '../lib/reports'

const PERIODS = [
  { key: 'month', label: 'This month' },
  { key: 'last', label: 'Last month' },
  { key: 'quarter', label: 'Last 3 months' },
  { key: 'year', label: 'This year' },
]

const TYPE_META = {
  expense: { Icon: ArrowUpRight, className: 'text-expense' },
  income: { Icon: ArrowDownLeft, className: 'text-income' },
  refund: { Icon: Undo2, className: 'text-income' },
  transfer: { Icon: ArrowLeftRight, className: 'text-text-muted' },
}

const BUDGET_STATE = {
  ok: 'bg-income',
  warning: 'bg-warning',
  critical: 'bg-expense',
  exceeded: 'bg-expense',
}

function Stat({ label, value, hint, tone = 'text-text', icon: Icon }) {
  return (
    <section className="card p-4" aria-label={label}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</p>
        {Icon && <Icon size={15} className="text-text-muted" aria-hidden="true" />}
      </div>
      <p className={`mt-2 text-xl font-semibold tracking-tight ${tone}`}>{value}</p>
      <p className="mt-1 text-xs text-text-muted">{hint}</p>
    </section>
  )
}

export default function Dashboard() {
  const [period, setPeriod] = useState('month')
  const range = useMemo(() => rangeFor(period), [period])

  const profileQuery = useQuery({
    queryKey: ['me'],
    queryFn: async () => (await api.get('/me')).data.data,
  })
  const overviewQuery = useQuery({
    queryKey: ['report-overview', range],
    queryFn: async () => (await api.get('/reports/overview', { params: range })).data.data,
  })
  const budgetsQuery = useBudgets()
  const billsQuery = useBills()
  const currenciesQuery = useCurrencies()

  const report = overviewQuery.data
  const budgets = budgetsQuery.data ?? []
  const currencies = currenciesQuery.data ?? []

  const today = todayISO()
  const horizon = addDaysISO(today, 30)
  const upcomingBills = (billsQuery.data ?? []).filter(
    (bill) =>
      ['pending', 'overdue'].includes(bill.status) &&
      bill.due_date >= today &&
      bill.due_date <= horizon,
  )

  const firstName = profileQuery.data?.full_name?.split(' ')[0]
  const currency = report?.currency_code ?? 'NGN'
  const decimalPlaces =
    currencies.find((row) => row.code === currency)?.decimal_places ?? 2

  const totals = report?.totals
  const accounts = report?.accounts ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">
            {firstName ? `Welcome back, ${firstName}` : 'Dashboard'}
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Every figure below is calculated from your recorded transactions.
          </p>
        </div>

        <div
          className="inline-flex flex-wrap rounded-xl border border-border bg-surface p-1"
          role="group"
          aria-label="Reporting period"
        >
          {PERIODS.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-pressed={period === option.key}
              onClick={() => setPeriod(option.key)}
              className={[
                'rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors',
                period === option.key
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-muted hover:bg-surface-raised hover:text-text',
              ].join(' ')}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {profileQuery.isError && (
        <Alert variant="error" title="Could not load your profile">
          {apiErrorMessage(profileQuery.error)}
        </Alert>
      )}
      {overviewQuery.isError && (
        <Alert variant="error" title="Could not load your dashboard">
          {apiErrorMessage(overviewQuery.error)}
        </Alert>
      )}

      {overviewQuery.isLoading ? (
        <p className="text-sm text-text-muted">Loading your figures…</p>
      ) : (
        <>
          {report && accounts.length === 0 && (
            <section className="card p-6" aria-labelledby="start-heading">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Wallet size={18} aria-hidden="true" />
                </span>
                <div>
                  <h2 id="start-heading" className="text-sm font-semibold text-text">
                    Start with an account
                  </h2>
                  <p className="mt-1 max-w-xl text-sm text-text-muted">
                    Add where your money lives, then record your first transaction. This dashboard
                    will fill in automatically - there are no sample figures.
                  </p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <Link
                  to="/accounts"
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary transition-colors hover:opacity-90"
                >
                  <Plus size={15} aria-hidden="true" />
                  Add an account
                </Link>
                <Link
                  to="/categories"
                  className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-raised"
                >
                  Review categories
                </Link>
              </div>
            </section>
          )}

          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            {report?.period.label ?? 'Current period'}
            {report ? ` · ${report.totals.transaction_count} transactions` : ''}
          </p>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Income"
              icon={ArrowDownLeft}
              tone="text-income"
              value={formatMoney(totals?.income_minor ?? 0, currency, decimalPlaces)}
              hint="Money received from income transactions."
            />
            <Stat
              label="Spending"
              icon={ArrowUpRight}
              tone="text-expense"
              value={formatMoney(totals?.spending_minor ?? 0, currency, decimalPlaces)}
              hint={
                (totals?.refunds_minor ?? 0) > 0
                  ? `Gross expenses minus ${formatMoney(
                      totals.refunds_minor,
                      currency,
                      decimalPlaces,
                    )} in refunds.`
                  : 'Expenses minus refunds. Transfers are excluded.'
              }
            />
            <Stat
              label="Net"
              icon={PiggyBank}
              tone={(totals?.net_minor ?? 0) < 0 ? 'text-expense' : 'text-income'}
              value={formatMoney(totals?.net_minor ?? 0, currency, decimalPlaces)}
              hint="Income minus net spending."
            />
            <Stat
              label="Savings rate"
              icon={Target}
              value={totals?.savings_rate === null ? '—' : `${totals?.savings_rate ?? 0}%`}
              hint={
                totals?.savings_rate === null
                  ? 'Add income to calculate a savings rate.'
                  : 'Net as a share of income.'
              }
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-5">
            <section className="card p-5 lg:col-span-3" aria-labelledby="trend-heading">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 id="trend-heading" className="text-sm font-semibold text-text">
                  Income vs spending
                </h2>
                <div className="flex items-center gap-3 text-xs text-text-muted">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-chart-1" aria-hidden="true" />
                    Income
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-chart-5" aria-hidden="true" />
                    Spending
                  </span>
                </div>
              </div>
              <div className="mt-3">
                <TrendChart
                  data={report?.trend ?? []}
                  currency={currency}
                  decimalPlaces={decimalPlaces}
                />
              </div>
              <p className="sr-only">
                {(report?.trend ?? [])
                  .map(
                    (point) =>
                      `${point.label}: income ${formatMoney(
                        point.income_minor,
                        currency,
                        decimalPlaces,
                      )}, spending ${formatMoney(
                        point.spending_minor,
                        currency,
                        decimalPlaces,
                      )}.`,
                  )
                  .join(' ')}
              </p>
            </section>

            <section className="card p-5 lg:col-span-2" aria-labelledby="categories-heading">
              <h2 id="categories-heading" className="text-sm font-semibold text-text">
                Spending by category
              </h2>
              <div className="mt-3">
                {(report?.by_category ?? []).length === 0 ? (
                  <div className="py-8 text-center">
                    <p className="text-sm text-text-muted">No spending in this period.</p>
                    <Link
                      to="/transactions"
                      className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
                    >
                      Add a transaction
                      <ArrowRight size={13} aria-hidden="true" />
                    </Link>
                  </div>
                ) : (
                  <CategoryChart
                    data={report.by_category}
                    currency={currency}
                    decimalPlaces={decimalPlaces}
                  />
                )}
              </div>
            </section>
          </div>

          <div className="grid gap-4 lg:grid-cols-5">
            <section className="card p-5 lg:col-span-3" aria-labelledby="recent-heading">
              <div className="flex items-center justify-between gap-2">
                <h2 id="recent-heading" className="text-sm font-semibold text-text">
                  Recent transactions
                </h2>
                <Link
                  to="/transactions"
                  className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                >
                  View all
                  <ArrowRight size={13} aria-hidden="true" />
                </Link>
              </div>

              {(report?.recent ?? []).length === 0 ? (
                <p className="mt-4 text-sm text-text-muted">
                  No transactions in this period yet.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-border">
                  {report.recent.map((transaction) => {
                    const meta = TYPE_META[transaction.type]
                    const Icon = meta.Icon
                    return (
                      <li key={transaction.id} className="flex items-center gap-3 py-2.5">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-raised text-text-muted">
                          <Icon size={14} aria-hidden="true" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-text">
                            {transaction.vendor ||
                              transaction.description ||
                              transaction.category?.name ||
                              titleCase(transaction.type)}
                          </p>
                          <p className="truncate text-xs text-text-muted">
                            {formatDate(transaction.transaction_date)} ·{' '}
                            {transaction.account.name}
                          </p>
                        </div>
                        <p className={`text-sm font-medium ${meta.className}`}>
                          {transaction.type === 'expense' ? '−' : ''}
                          {formatMoney(
                            transaction.amount_minor,
                            transaction.currency_code,
                            decimalPlaces,
                          )}
                        </p>
                      </li>
                    )
                  })}
                </ul>
              )}
            </section>

            <div className="space-y-4 lg:col-span-2">
              <section className="card p-5" aria-labelledby="bills-heading">
                <div className="flex items-center justify-between gap-2">
                  <h2 id="bills-heading" className="text-sm font-semibold text-text">
                    Upcoming bills
                  </h2>
                  <Link
                    to="/recurring"
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    Manage
                    <ArrowRight size={13} aria-hidden="true" />
                  </Link>
                </div>

                {upcomingBills.length === 0 ? (
                  <p className="mt-3 text-sm text-text-muted">
                    No bills are due in the next 30 days.
                  </p>
                ) : (
                  <ul className="mt-2 divide-y divide-border">
                    {upcomingBills.slice(0, 4).map((bill) => (
                      <li key={bill.id} className="flex items-center gap-2 py-2">
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-xs text-text">
                            {bill.vendor || bill.description || bill.category_name || 'Bill'}
                          </span>
                          <span className="block text-[11px] text-text-muted">
                            {bill.status === 'overdue' ? 'Overdue · ' : ''}
                            {formatDate(bill.due_date)}
                          </span>
                        </span>
                        <span
                          className={`text-xs font-medium ${
                            bill.status === 'overdue' ? 'text-expense' : 'text-text'
                          }`}
                        >
                          {formatMoney(
                            bill.amount_minor,
                            bill.currency_code,
                            currencies.find((row) => row.code === bill.currency_code)
                              ?.decimal_places ?? 2,
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="card p-5" aria-labelledby="budgets-heading">
                <div className="flex items-center justify-between gap-2">
                  <h2 id="budgets-heading" className="text-sm font-semibold text-text">
                    Budgets
                  </h2>
                  <Link
                    to="/budgets"
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    Manage
                    <ArrowRight size={13} aria-hidden="true" />
                  </Link>
                </div>

                {budgets.length === 0 ? (
                  <p className="mt-3 text-sm text-text-muted">
                    No budgets yet. Set a limit to track progress here.
                  </p>
                ) : (
                  <ul className="mt-3 space-y-3">
                    {budgets.slice(0, 3).map((budget) => (
                      <li key={budget.id}>
                        <div className="flex items-center justify-between gap-2 text-xs">
                          <span className="truncate font-medium text-text">{budget.name}</span>
                          <span className="shrink-0 text-text-muted">{budget.percent_used}%</span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-raised">
                          <div
                            className={`h-full rounded-full ${
                              BUDGET_STATE[budget.state] ?? 'bg-income'
                            }`}
                            style={{ width: `${Math.min(budget.percent_used, 100)}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="card p-5" aria-labelledby="accounts-heading">
                <div className="flex items-center justify-between gap-2">
                  <h2 id="accounts-heading" className="text-sm font-semibold text-text">
                    Accounts
                  </h2>
                  <Link
                    to="/accounts"
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    Manage
                    <ArrowRight size={13} aria-hidden="true" />
                  </Link>
                </div>

                {accounts.length === 0 ? (
                  <p className="mt-3 text-sm text-text-muted">No accounts yet.</p>
                ) : (
                  <ul className="mt-2 divide-y divide-border">
                    {accounts.slice(0, 4).map((account) => (
                      <li key={account.id} className="flex items-center gap-2 py-2">
                        <Landmark size={14} className="text-text-muted" aria-hidden="true" />
                        <span className="min-w-0 flex-1 truncate text-xs text-text">
                          {account.name}
                        </span>
                        <span
                          className={`text-xs font-medium ${
                            account.balance_minor < 0 ? 'text-expense' : 'text-text'
                          }`}
                        >
                          {formatMoney(
                            account.balance_minor,
                            account.currency_code,
                            currencies.find((row) => row.code === account.currency_code)
                              ?.decimal_places ?? 2,
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
