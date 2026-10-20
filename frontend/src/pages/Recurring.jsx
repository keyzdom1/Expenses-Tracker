import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CalendarClock,
  Check,
  Pause,
  Pencil,
  Plus,
  ReceiptText,
  RefreshCw,
  Repeat,
  SkipForward,
} from 'lucide-react'
import { useState } from 'react'

import RecurringForm from '../components/recurring/RecurringForm'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import Modal from '../components/ui/Modal'
import {
  useAccounts,
  useBills,
  useCategories,
  useCurrencies,
  useRecurring,
} from '../hooks/useReferenceData'
import { api, apiErrorMessage } from '../lib/api'
import { formatDate, formatMoney, titleCase } from '../lib/format'

const BILL_STATE = {
  pending: { label: 'Pending', className: 'bg-warning-soft text-warning' },
  overdue: { label: 'Overdue', className: 'bg-expense-soft text-expense' },
  paid: { label: 'Paid', className: 'bg-income-soft text-income' },
  skipped: { label: 'Skipped', className: 'bg-surface-raised text-text-muted' },
}

const FILTERS = [
  { key: 'open', label: 'Open' },
  { key: 'paid', label: 'Paid' },
  { key: 'skipped', label: 'Skipped' },
  { key: 'all', label: 'All' },
]

function billTitle(bill) {
  return bill.vendor || bill.description || bill.category_name || titleCase(bill.type)
}

export default function Recurring() {
  const queryClient = useQueryClient()
  const [modal, setModal] = useState(null)
  const [filter, setFilter] = useState('open')
  const [actionTarget, setActionTarget] = useState(null)
  const [pauseTarget, setPauseTarget] = useState(null)
  const [jobMessage, setJobMessage] = useState('')
  const [jobError, setJobError] = useState('')

  const billsQuery = useBills()
  const recurringQuery = useRecurring({ includeInactive: true })
  const accountsQuery = useAccounts()
  const categoriesQuery = useCategories()
  const currenciesQuery = useCurrencies()

  const bills = billsQuery.data ?? []
  const recurringItems = recurringQuery.data ?? []
  const accounts = accountsQuery.data ?? []
  const categories = categoriesQuery.data ?? []
  const currencies = currenciesQuery.data ?? []

  const decimalPlacesFor = (code) =>
    currencies.find((currency) => currency.code === code)?.decimal_places ?? 2

  const openBills = bills.filter((bill) => ['pending', 'overdue'].includes(bill.status))
  const visibleBills = bills.filter((bill) => {
    if (filter === 'all') return true
    if (filter === 'open') return ['pending', 'overdue'].includes(bill.status)
    return bill.status === filter
  })

  const invalidateMoney = () => {
    queryClient.invalidateQueries({ queryKey: ['bills'] })
    queryClient.invalidateQueries({ queryKey: ['transactions'] })
    queryClient.invalidateQueries({ queryKey: ['accounts'] })
    queryClient.invalidateQueries({ queryKey: ['budgets'] })
    queryClient.invalidateQueries({ queryKey: ['report-overview'] })
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
  }

  const generateMutation = useMutation({
    mutationFn: async () => (await api.post('/jobs/run/me')).data.data,
    onSuccess: (result) => {
      setJobError('')
      setJobMessage(
        result.bills_created === 0
          ? 'No new bills were due. Everything is up to date.'
          : `Generated ${result.bills_created} bill${result.bills_created === 1 ? '' : 's'}.`,
      )
      invalidateMoney()
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
    onError: (error) => {
      setJobMessage('')
      setJobError(apiErrorMessage(error, 'Could not generate bills right now.'))
    },
  })

  const settleMutation = useMutation({
    mutationFn: ({ bill, action }) => api.post(`/bills/${bill.id}/${action}`),
    onSuccess: () => {
      invalidateMoney()
      setActionTarget(null)
    },
  })

  const pauseMutation = useMutation({
    mutationFn: (template) => api.delete(`/recurring/${template.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      setPauseTarget(null)
    },
  })

  const handleSaved = () => {
    setModal(null)
    queryClient.invalidateQueries({ queryKey: ['recurring'] })
    // A new template should immediately show its upcoming bill.
    generateMutation.mutate()
  }

  const actionIsPay = actionTarget?.action === 'pay'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Recurring &amp; bills</h1>
          <p className="mt-1 text-sm text-text-muted">
            Templates generate bill occurrences. Paying a bill records the matching transaction.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => generateMutation.mutate()}
            isLoading={generateMutation.isPending}
          >
            <RefreshCw size={15} aria-hidden="true" />
            Generate due bills
          </Button>
          <Button onClick={() => setModal({ mode: 'create' })} disabled={accounts.length === 0}>
            <Plus size={16} aria-hidden="true" />
            Add recurring
          </Button>
        </div>
      </div>

      {accounts.length === 0 && (
        <Alert variant="info" title="Add an account first">
          Recurring templates need an account to pay from or receive into.
        </Alert>
      )}

      {jobMessage && (
        <p role="status" className="text-xs text-income">
          {jobMessage}
        </p>
      )}
      {jobError && (
        <Alert variant="error" title="Bills were not generated">
          {jobError}
        </Alert>
      )}

      <section className="card p-5" aria-labelledby="bills-heading">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="bills-heading" className="text-sm font-semibold text-text">
              Bills
            </h2>
            <p className="mt-1 text-xs text-text-muted">
              {openBills.length === 0
                ? 'No open bills.'
                : `${openBills.length} open bill${openBills.length === 1 ? '' : 's'}.`}
            </p>
          </div>

          <div
            className="inline-flex flex-wrap rounded-xl border border-border bg-surface p-1"
            role="group"
            aria-label="Filter bills"
          >
            {FILTERS.map((option) => (
              <button
                key={option.key}
                type="button"
                aria-pressed={filter === option.key}
                onClick={() => setFilter(option.key)}
                className={[
                  'rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors',
                  filter === option.key
                    ? 'bg-primary/10 text-primary'
                    : 'text-text-muted hover:bg-surface-raised hover:text-text',
                ].join(' ')}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {billsQuery.isError && (
          <Alert variant="error" title="Could not load bills">
            {apiErrorMessage(billsQuery.error)}
          </Alert>
        )}

        {billsQuery.isLoading ? (
          <p className="mt-4 text-sm text-text-muted">Loading bills…</p>
        ) : visibleBills.length === 0 ? (
          <div className="py-8 text-center">
            <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ReceiptText size={20} aria-hidden="true" />
            </span>
            <p className="mt-3 text-sm text-text-muted">
              {bills.length === 0
                ? 'No bills yet. Create a template, then generate its first occurrence.'
                : 'Nothing matches this filter.'}
            </p>
          </div>
        ) : (
          <ul className="mt-3 divide-y divide-border">
            {visibleBills.map((bill) => {
              const state = BILL_STATE[bill.status] ?? BILL_STATE.pending
              const isOpen = ['pending', 'overdue'].includes(bill.status)
              return (
                <li
                  key={bill.id}
                  className="flex flex-wrap items-center gap-3 py-3"
                  aria-label={`${billTitle(bill)} due ${bill.due_date}`}
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-raised text-text-muted">
                    <CalendarClock size={14} aria-hidden="true" />
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-text">{billTitle(bill)}</p>
                    <p className="truncate text-xs text-text-muted">
                      {formatDate(bill.due_date)} ·{' '}
                      {bill.type === 'transfer'
                        ? `${bill.account_name} to ${bill.destination_account_name ?? 'account'}`
                        : bill.account_name}
                      {bill.category_name ? ` · ${bill.category_name}` : ''}
                    </p>
                  </div>

                  <div className="text-right">
                    <p className="text-sm font-medium text-text">
                      {formatMoney(
                        bill.amount_minor,
                        bill.currency_code,
                        decimalPlacesFor(bill.currency_code),
                      )}
                    </p>
                    <span className={`badge mt-1 ${state.className}`}>{state.label}</span>
                  </div>

                  {isOpen && (
                    <div className="flex w-full gap-2 sm:w-auto">
                      <Button
                        size="sm"
                        onClick={() => setActionTarget({ bill, action: 'pay' })}
                      >
                        <Check size={14} aria-hidden="true" />
                        Pay
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setActionTarget({ bill, action: 'skip' })}
                      >
                        <SkipForward size={14} aria-hidden="true" />
                        Skip
                      </Button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="space-y-3" aria-labelledby="templates-heading">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 id="templates-heading" className="text-sm font-semibold text-text">
              Recurring templates
            </h2>
            <p className="mt-1 text-xs text-text-muted">
              Paused templates keep their history and can be edited or resumed.
            </p>
          </div>
          <span className="text-xs text-text-muted">
            {recurringItems.filter((item) => item.is_active).length} active
          </span>
        </div>

        {recurringQuery.isError && (
          <Alert variant="error" title="Could not load recurring templates">
            {apiErrorMessage(recurringQuery.error)}
          </Alert>
        )}

        {recurringQuery.isLoading ? (
          <p className="text-sm text-text-muted">Loading templates…</p>
        ) : recurringItems.length === 0 ? (
          <section className="card p-8 text-center">
            <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Repeat size={20} aria-hidden="true" />
            </span>
            <h3 className="mt-3 text-sm font-semibold text-text">No recurring templates</h3>
            <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">
              Add rent, subscriptions or a monthly transfer. Each occurrence becomes a bill you
              can pay or skip.
            </p>
            {accounts.length > 0 && (
              <Button className="mt-4" onClick={() => setModal({ mode: 'create' })}>
                <Plus size={16} aria-hidden="true" />
                Create your first template
              </Button>
            )}
          </section>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {recurringItems.map((template) => (
              <article key={template.id} className="card p-4" aria-label={titleCase(template.type)}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-text">
                      {template.vendor || template.description || titleCase(template.type)}
                    </p>
                    <p className="mt-1 text-xs text-text-muted">
                      {titleCase(template.type)} · every {template.interval_count}{' '}
                      {template.frequency}
                      {template.interval_count === 1 ? '' : 's'}
                    </p>
                  </div>
                  <span
                    className={`badge ${
                      template.is_active
                        ? 'bg-income-soft text-income'
                        : 'bg-surface-raised text-text-muted'
                    }`}
                  >
                    {template.is_active ? 'Active' : 'Paused'}
                  </span>
                </div>

                <p className="mt-3 text-lg font-semibold text-text">
                  {formatMoney(
                    template.amount_minor,
                    template.currency_code,
                    decimalPlacesFor(template.currency_code),
                  )}
                  <span className="ml-1 text-xs font-normal text-text-muted">
                    {template.frequency}
                  </span>
                </p>

                <dl className="mt-2 space-y-1 text-xs text-text-muted">
                  <div className="flex justify-between gap-2">
                    <dt>Account</dt>
                    <dd className="truncate text-right text-text">
                      {template.type === 'transfer'
                        ? `${template.account.name} to ${
                            template.destination_account?.name ?? 'account'
                          }`
                        : template.account.name}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>Next occurrence</dt>
                    <dd className="text-right text-text">{formatDate(template.next_occurrence)}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>Reminder</dt>
                    <dd className="text-right text-text">
                      {template.reminder_days === 0
                        ? 'On the due date'
                        : `${template.reminder_days} day${
                            template.reminder_days === 1 ? '' : 's'
                          } before`}
                    </dd>
                  </div>
                </dl>

                <div className="mt-3 flex justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => setModal({ mode: 'edit', template })}
                    aria-label={`Edit ${template.vendor || titleCase(template.type)}`}
                    className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
                  >
                    <Pencil size={15} aria-hidden="true" />
                  </button>
                  {template.is_active && (
                    <button
                      type="button"
                      onClick={() => setPauseTarget(template)}
                      aria-label={`Pause ${template.vendor || titleCase(template.type)}`}
                      className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-expense"
                    >
                      <Pause size={15} aria-hidden="true" />
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <Modal
        open={modal !== null}
        onClose={() => setModal(null)}
        size="lg"
        title={modal?.mode === 'edit' ? 'Edit recurring template' : 'Add recurring template'}
        description="Bills are generated up to a week ahead so reminders reach you in time."
      >
        {modal && (
          <RecurringForm
            key={modal.template?.id ?? 'new'}
            recurring={modal.template}
            accounts={accounts}
            categories={categories}
            currencies={currencies}
            onClose={() => setModal(null)}
            onSaved={handleSaved}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={actionTarget !== null}
        onClose={() => {
          setActionTarget(null)
          settleMutation.reset()
        }}
        onConfirm={() =>
          settleMutation.mutate({ bill: actionTarget.bill, action: actionTarget.action })
        }
        title={
          actionIsPay
            ? `Pay ${actionTarget ? billTitle(actionTarget.bill) : 'bill'}?`
            : `Skip ${actionTarget ? billTitle(actionTarget.bill) : 'bill'}?`
        }
        description={
          actionIsPay
            ? 'This records a real transaction for the bill amount on its due date.'
            : 'No transaction will be recorded. The occurrence stays in your history as skipped.'
        }
        confirmLabel={actionIsPay ? 'Pay bill' : 'Skip bill'}
        variant={actionIsPay ? 'primary' : 'danger'}
        isPending={settleMutation.isPending}
        errorMessage={settleMutation.isError ? apiErrorMessage(settleMutation.error) : null}
      />

      <ConfirmDialog
        open={pauseTarget !== null}
        onClose={() => {
          setPauseTarget(null)
          pauseMutation.reset()
        }}
        onConfirm={() => pauseMutation.mutate(pauseTarget)}
        title={`Pause ${pauseTarget?.vendor ?? 'this template'}?`}
        description="No further bills will be generated. Existing bills and transactions stay untouched."
        confirmLabel="Pause template"
        isPending={pauseMutation.isPending}
        errorMessage={pauseMutation.isError ? apiErrorMessage(pauseMutation.error) : null}
      />
    </div>
  )
}
