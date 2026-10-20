import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Target, Trash2 } from 'lucide-react'
import { useState } from 'react'

import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import Input from '../components/ui/Input'
import Modal from '../components/ui/Modal'
import Select from '../components/ui/Select'
import {
  useBudgets,
  useCategories,
  useCurrencies,
  usePreferences,
} from '../hooks/useReferenceData'
import { api, apiErrorMessage } from '../lib/api'
import {
  formatDate,
  formatMoney,
  minorToInput,
  parseAmountInput,
  titleCase,
  todayISO,
} from '../lib/format'

const PERIODS = ['weekly', 'monthly', 'quarterly', 'yearly', 'custom']

const STATE_META = {
  ok: { label: 'On track', className: 'bg-income-soft text-income', bar: 'bg-income' },
  warning: { label: 'Watch', className: 'bg-warning-soft text-warning', bar: 'bg-warning' },
  critical: { label: 'Critical', className: 'bg-expense-soft text-expense', bar: 'bg-expense' },
  exceeded: { label: 'Over budget', className: 'bg-expense-soft text-expense', bar: 'bg-expense' },
}

function BudgetForm({ budget, categories, currencies, defaultCurrency, onClose, onSaved }) {
  const queryClient = useQueryClient()
  const isEdit = Boolean(budget)

  const [name, setName] = useState(budget?.name ?? '')
  const [amount, setAmount] = useState(() => {
    if (!budget) return ''
    const currency = currencies.find((row) => row.code === budget.currency_code)
    return minorToInput(budget.amount_minor, currency?.decimal_places ?? 2)
  })
  const [currency, setCurrency] = useState(budget?.currency_code ?? defaultCurrency)
  const [categoryId, setCategoryId] = useState(budget?.category_id ?? '')
  const [period, setPeriod] = useState(budget?.period ?? 'monthly')
  const [warning, setWarning] = useState(String(budget?.warning_threshold ?? 80))
  const [critical, setCritical] = useState(String(budget?.critical_threshold ?? 90))
  const [startDate, setStartDate] = useState(budget?.start_date ?? todayISO())
  const [endDate, setEndDate] = useState(budget?.end_date ?? '')
  const [error, setError] = useState('')

  const decimalPlaces =
    currencies.find((row) => row.code === currency)?.decimal_places ?? 2

  const expenseCategories = categories.filter((row) => row.kind === 'expense')
  const categoryOptions = expenseCategories.map((row) => {
    const parent = row.parent_id
      ? expenseCategories.find((candidate) => candidate.id === row.parent_id)
      : null
    return { value: row.id, label: parent ? `${parent.name} / ${row.name}` : row.name }
  })

  const mutation = useMutation({
    mutationFn: (payload) =>
      isEdit ? api.patch(`/budgets/${budget.id}`, payload) : api.post('/budgets', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      onSaved()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError)),
  })

  const handleSubmit = (event) => {
    event.preventDefault()
    setError('')

    if (!name.trim()) {
      setError('Give the budget a name.')
      return
    }

    const amountMinor = parseAmountInput(amount, decimalPlaces)
    if (amountMinor === null || amountMinor <= 0) {
      setError('Enter a budget amount greater than zero.')
      return
    }

    const warningValue = Number(warning)
    const criticalValue = Number(critical)
    if (
      !Number.isInteger(warningValue) ||
      !Number.isInteger(criticalValue) ||
      warningValue < 1 ||
      criticalValue > 100 ||
      warningValue > criticalValue
    ) {
      setError('Thresholds must be whole numbers between 1 and 100, with warning at or below critical.')
      return
    }

    if (period === 'custom' && !endDate) {
      setError('A custom budget needs an end date.')
      return
    }

    const payload = {
      name: name.trim(),
      amount_minor: amountMinor,
      category_id: categoryId || null,
      period,
      warning_threshold: warningValue,
      critical_threshold: criticalValue,
      start_date: startDate,
      end_date: period === 'custom' ? endDate : null,
    }
    if (!isEdit) payload.currency_code = currency

    mutation.mutate(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <Alert variant="error">{error}</Alert>}

      <Input
        label="Budget name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Monthly groceries"
        maxLength={120}
        required
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label={`Limit (${currency})`}
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          inputMode="decimal"
          placeholder="0.00"
          required
        />
        {isEdit ? (
          <Input label="Currency" value={currency} disabled readOnly />
        ) : (
          <Select
            label="Currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value)}
            options={currencies.map((row) => ({
              value: row.code,
              label: `${row.code} - ${row.name}`,
            }))}
          />
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Category"
          value={categoryId}
          onChange={(event) => setCategoryId(event.target.value)}
          placeholder="All spending (overall)"
          options={categoryOptions}
          hint="Leave empty to budget every expense category together."
        />
        <Select
          label="Period"
          value={period}
          onChange={(event) => setPeriod(event.target.value)}
          options={PERIODS.map((value) => ({ value, label: titleCase(value) }))}
        />
      </div>

      {period === 'custom' && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Starts"
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
          <Input
            label="Ends"
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            required
          />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Warning threshold (%)"
          type="number"
          min="1"
          max="100"
          value={warning}
          onChange={(event) => setWarning(event.target.value)}
          hint="Shown when spending reaches this percentage."
        />
        <Input
          label="Critical threshold (%)"
          type="number"
          min="1"
          max="100"
          value={critical}
          onChange={(event) => setCritical(event.target.value)}
          hint="Must be at or above the warning threshold."
        />
      </div>

      <div className="flex justify-end gap-2 pt-1">
        <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button type="submit" isLoading={mutation.isPending}>
          {isEdit ? 'Save budget' : 'Create budget'}
        </Button>
      </div>
    </form>
  )
}

export default function Budgets() {
  const queryClient = useQueryClient()
  const [modal, setModal] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const budgetsQuery = useBudgets()
  const categoriesQuery = useCategories()
  const currenciesQuery = useCurrencies()
  const preferencesQuery = usePreferences()

  const budgets = budgetsQuery.data ?? []
  const currencies = currenciesQuery.data ?? []
  const categories = categoriesQuery.data ?? []

  const decimalPlacesFor = (code) =>
    currencies.find((currency) => currency.code === code)?.decimal_places ?? 2

  const deleteMutation = useMutation({
    mutationFn: (budget) => api.delete(`/budgets/${budget.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      setDeleteTarget(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Budgets</h1>
          <p className="mt-1 text-sm text-text-muted">
            Limits are compared with real net spending - expenses minus refunds. Transfers never
            count.
          </p>
        </div>
        <Button onClick={() => setModal({ mode: 'create' })}>
          <Plus size={16} aria-hidden="true" />
          Add budget
        </Button>
      </div>

      {budgetsQuery.isError && (
        <Alert variant="error" title="Could not load budgets">
          {apiErrorMessage(budgetsQuery.error)}
        </Alert>
      )}

      {budgetsQuery.isLoading ? (
        <p className="text-sm text-text-muted">Loading budgets…</p>
      ) : budgets.length === 0 ? (
        <section className="card p-8 text-center">
          <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Target size={20} aria-hidden="true" />
          </span>
          <h2 className="mt-3 text-sm font-semibold text-text">No budgets yet</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">
            Set a monthly limit for a category, or one overall limit. Progress comes straight from
            your transactions.
          </p>
          <Button className="mt-4" onClick={() => setModal({ mode: 'create' })}>
            <Plus size={16} aria-hidden="true" />
            Create your first budget
          </Button>
        </section>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {budgets.map((budget) => {
            const state = STATE_META[budget.state] ?? STATE_META.ok
            const width = Math.min(Math.max(budget.percent_used, 0), 100)

            return (
              <article key={budget.id} className="card p-5" aria-label={budget.name}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate text-sm font-semibold text-text">{budget.name}</h2>
                    <p className="mt-1 text-xs text-text-muted">
                      {budget.category_name ?? 'All expenses'} · {titleCase(budget.period)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <span className={`badge ${state.className}`}>{state.label}</span>
                    <button
                      type="button"
                      onClick={() => setModal({ mode: 'edit', budget })}
                      aria-label={`Edit ${budget.name}`}
                      className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
                    >
                      <Pencil size={15} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(budget)}
                      aria-label={`Delete ${budget.name}`}
                      className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-expense"
                    >
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </div>
                </div>

                <div className="mt-4 flex items-end justify-between gap-3">
                  <p className="text-lg font-semibold text-text">
                    {formatMoney(
                      budget.spent_minor,
                      budget.currency_code,
                      decimalPlacesFor(budget.currency_code),
                    )}
                    <span className="ml-1 text-xs font-normal text-text-muted">
                      of{' '}
                      {formatMoney(
                        budget.amount_minor,
                        budget.currency_code,
                        decimalPlacesFor(budget.currency_code),
                      )}
                    </span>
                  </p>
                  <span className="text-xs font-medium text-text-muted">
                    {budget.percent_used}%
                  </span>
                </div>

                <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-raised">
                  <div
                    className={`h-full rounded-full transition-all ${state.bar}`}
                    style={{ width: `${width}%` }}
                  />
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-text-muted">
                  <span>
                    {budget.remaining_minor >= 0
                      ? `${formatMoney(
                          budget.remaining_minor,
                          budget.currency_code,
                          decimalPlacesFor(budget.currency_code),
                        )} left`
                      : `Over by ${formatMoney(
                          Math.abs(budget.remaining_minor),
                          budget.currency_code,
                          decimalPlacesFor(budget.currency_code),
                        )}`}
                  </span>
                  <span>
                    {formatDate(budget.period_start)} - {formatDate(budget.period_end)}
                  </span>
                </div>
              </article>
            )
          })}
        </div>
      )}

      <Modal
        open={modal !== null}
        onClose={() => setModal(null)}
        title={modal?.mode === 'edit' ? 'Edit budget' : 'Add budget'}
        description="Actuals are recalculated from your transactions every time this page loads."
      >
        {modal && (
          <BudgetForm
            key={modal.budget?.id ?? 'new'}
            budget={modal.budget}
            categories={categories}
            currencies={currencies}
            defaultCurrency={preferencesQuery.data?.currency_code ?? 'NGN'}
            onClose={() => setModal(null)}
            onSaved={() => setModal(null)}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        onClose={() => {
          setDeleteTarget(null)
          deleteMutation.reset()
        }}
        onConfirm={() => deleteMutation.mutate(deleteTarget)}
        title={`Delete ${deleteTarget?.name ?? 'budget'}?`}
        description="The budget disappears but your transactions are untouched."
        confirmLabel="Delete budget"
        isPending={deleteMutation.isPending}
        errorMessage={deleteMutation.isError ? apiErrorMessage(deleteMutation.error) : null}
      />
    </div>
  )
}
