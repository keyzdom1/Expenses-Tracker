import { useMutation, useQuery } from '@tanstack/react-query'
import { Download, Printer } from 'lucide-react'
import { useState } from 'react'

import { CategoryChart, TrendChart } from '../components/dashboard/FinanceCharts'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import { useCurrencies } from '../hooks/useReferenceData'
import { api, apiErrorMessage } from '../lib/api'
import { formatDate, formatMoney } from '../lib/format'
import { filenameFromDisposition, rangeFor, REPORT_PRESETS } from '../lib/reports'

function Summary({ label, value, hint, tone = 'text-text' }) {
  return (
    <section className="card p-4" aria-label={label}>
      <p className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</p>
      <p className={`mt-2 text-xl font-semibold tracking-tight ${tone}`}>{value}</p>
      <p className="mt-1 text-xs text-text-muted">{hint}</p>
    </section>
  )
}

export default function Reports() {
  const [preset, setPreset] = useState('month')
  const [range, setRange] = useState(() => rangeFor('month'))
  const [downloadMessage, setDownloadMessage] = useState('')

  const currenciesQuery = useCurrencies()
  const currencies = currenciesQuery.data ?? []

  const rangeError =
    !range.dateFrom || !range.dateTo
      ? 'Choose both a start and an end date.'
      : range.dateFrom > range.dateTo
        ? 'The start date must be on or before the end date.'
        : ''

  const reportQuery = useQuery({
    queryKey: ['report-overview', 'reports-page', range],
    queryFn: async () => (await api.get('/reports/overview', { params: range })).data.data,
    enabled: !rangeError,
  })

  const csvMutation = useMutation({
    mutationFn: async () => {
      const response = await api.get('/reports/transactions.csv', {
        params: range,
        responseType: 'blob',
      })
      const filename = filenameFromDisposition(response.headers['content-disposition'])
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      return filename
    },
    onSuccess: (filename) => setDownloadMessage(`Downloaded ${filename}.`),
    onError: () => setDownloadMessage(''),
  })

  const report = reportQuery.data
  const currency = report?.currency_code ?? 'NGN'
  const decimalPlaces = currencies.find((row) => row.code === currency)?.decimal_places ?? 2
  const totals = report?.totals

  const choosePreset = (key) => {
    setPreset(key)
    setRange(rangeFor(key))
    setDownloadMessage('')
  }

  const changeDate = (key, value) => {
    setPreset('custom')
    setRange((current) => ({ ...current, [key]: value }))
    setDownloadMessage('')
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Reports</h1>
          <p className="mt-1 text-sm text-text-muted">
            Pick any period, export the underlying transactions, or print the summary.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => csvMutation.mutate()}
            disabled={Boolean(rangeError)}
            isLoading={csvMutation.isPending}
          >
            <Download size={15} aria-hidden="true" />
            Export CSV
          </Button>
          <Button variant="secondary" onClick={() => window.print()} disabled={!report}>
            <Printer size={15} aria-hidden="true" />
            Print
          </Button>
        </div>
      </div>

      <section className="card p-4 print:hidden" aria-label="Report period">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="grid flex-1 gap-4 sm:grid-cols-2 lg:max-w-md">
            <Input
              label="From"
              type="date"
              value={range.dateFrom}
              onChange={(event) => changeDate('dateFrom', event.target.value)}
            />
            <Input
              label="To"
              type="date"
              value={range.dateTo}
              onChange={(event) => changeDate('dateTo', event.target.value)}
            />
          </div>

          <div
            className="inline-flex flex-wrap rounded-xl border border-border bg-surface p-1"
            role="group"
            aria-label="Report presets"
          >
            {REPORT_PRESETS.map((option) => (
              <button
                key={option.key}
                type="button"
                aria-pressed={preset === option.key}
                onClick={() => choosePreset(option.key)}
                className={[
                  'rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors',
                  preset === option.key
                    ? 'bg-primary/10 text-primary'
                    : 'text-text-muted hover:bg-surface-raised hover:text-text',
                ].join(' ')}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {rangeError && <Alert variant="error" title="Check the dates">{rangeError}</Alert>}

      {reportQuery.isError && (
        <Alert variant="error" title="Could not build this report">
          {apiErrorMessage(reportQuery.error, 'The report could not be generated for that period.')}
        </Alert>
      )}

      {csvMutation.isError && (
        <Alert variant="error" title="Export failed">
          {apiErrorMessage(csvMutation.error, 'The CSV could not be downloaded. Try again.')}
        </Alert>
      )}

      {downloadMessage && (
        <p role="status" className="text-xs text-income">
          {downloadMessage}
        </p>
      )}

      {reportQuery.isLoading ? (
        <p className="text-sm text-text-muted">Building your report…</p>
      ) : report ? (
        <div className="space-y-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Report period</p>
            <h2 className="mt-1 text-lg font-semibold text-text">{report.period.label}</h2>
            <p className="mt-1 text-xs text-text-muted">
              {formatDate(report.period.date_from)} - {formatDate(report.period.date_to)} ·{' '}
              {totals.transaction_count} transactions in {currency}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Summary
              label="Income"
              tone="text-income"
              value={formatMoney(totals.income_minor, currency, decimalPlaces)}
              hint="Recorded income in this period."
            />
            <Summary
              label="Spending"
              tone="text-expense"
              value={formatMoney(totals.spending_minor, currency, decimalPlaces)}
              hint="Expenses minus refunds. Transfers are excluded."
            />
            <Summary
              label="Refunds"
              value={formatMoney(totals.refunds_minor, currency, decimalPlaces)}
              hint="Refunds reduce net spending."
            />
            <Summary
              label="Net"
              tone={totals.net_minor < 0 ? 'text-expense' : 'text-income'}
              value={formatMoney(totals.net_minor, currency, decimalPlaces)}
              hint={
                totals.savings_rate === null
                  ? 'No income in this period.'
                  : `Savings rate ${totals.savings_rate}%.`
              }
            />
          </div>

          <section className="card p-5" aria-labelledby="report-trend-heading">
            <h2 id="report-trend-heading" className="text-sm font-semibold text-text">
              Six-month trend
            </h2>
            <p className="mt-1 text-xs text-text-muted">
              Monthly income and net spending ending with the report period.
            </p>
            <div className="mt-3">
              <TrendChart data={report.trend} currency={currency} decimalPlaces={decimalPlaces} />
            </div>
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="card p-5" aria-labelledby="report-category-heading">
              <h2 id="report-category-heading" className="text-sm font-semibold text-text">
                Spending by category
              </h2>
              <div className="mt-3">
                {report.by_category.length === 0 ? (
                  <p className="py-8 text-center text-sm text-text-muted">
                    No spending in this period.
                  </p>
                ) : (
                  <CategoryChart
                    data={report.by_category}
                    currency={currency}
                    decimalPlaces={decimalPlaces}
                  />
                )}
              </div>
            </section>

            <section className="card p-5" aria-labelledby="report-table-heading">
              <h2 id="report-table-heading" className="text-sm font-semibold text-text">
                Category totals
              </h2>
              {report.by_category.length === 0 ? (
                <p className="mt-3 text-sm text-text-muted">Nothing to break down yet.</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-border text-text-muted">
                        <th scope="col" className="py-2 pr-3 font-medium">
                          Category
                        </th>
                        <th scope="col" className="py-2 pr-3 text-right font-medium">
                          Share
                        </th>
                        <th scope="col" className="py-2 text-right font-medium">
                          Spent
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {report.by_category.map((slice) => (
                        <tr key={slice.category_id ?? slice.name}>
                          <td className="py-2 pr-3 text-text">{slice.name}</td>
                          <td className="py-2 pr-3 text-right text-text-muted">{slice.share}%</td>
                          <td className="py-2 text-right font-medium text-text">
                            {formatMoney(slice.spent_minor, currency, decimalPlaces)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          <section className="card p-5" aria-labelledby="report-accounts-heading">
            <h2 id="report-accounts-heading" className="text-sm font-semibold text-text">
              Account balances now
            </h2>
            <p className="mt-1 text-xs text-text-muted">
              Balances are calculated from every transaction to date, not just this report period.
            </p>
            {report.accounts.length === 0 ? (
              <p className="mt-3 text-sm text-text-muted">No accounts yet.</p>
            ) : (
              <ul className="mt-2 divide-y divide-border">
                {report.accounts.map((account) => {
                  const places =
                    currencies.find((row) => row.code === account.currency_code)?.decimal_places ??
                    2
                  return (
                    <li key={account.id} className="flex items-center gap-3 py-2">
                      <span className="min-w-0 flex-1 truncate text-sm text-text">
                        {account.name}
                      </span>
                      <span
                        className={`text-sm font-medium ${
                          account.balance_minor < 0 ? 'text-expense' : 'text-text'
                        }`}
                      >
                        {formatMoney(account.balance_minor, account.currency_code, places)}
                      </span>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </div>
  )
}
