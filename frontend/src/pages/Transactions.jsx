import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Pencil,
  Plus,
  Search,
  Trash2,
  Undo2,
} from 'lucide-react'
import { useDeferredValue, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import TransactionForm from '../components/transactions/TransactionForm'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import Input from '../components/ui/Input'
import Modal from '../components/ui/Modal'
import Select from '../components/ui/Select'
import {
  useAccounts,
  useCategories,
  useCurrencies,
  usePreferences,
} from '../hooks/useReferenceData'
import { api, apiErrorMessage } from '../lib/api'
import { formatDate, formatMoney, titleCase } from '../lib/format'

const TYPE_META = {
  expense: { label: 'Expense', className: 'bg-expense-soft text-expense', Icon: ArrowUpRight },
  income: { label: 'Income', className: 'bg-income-soft text-income', Icon: ArrowDownLeft },
  refund: { label: 'Refund', className: 'bg-income-soft text-income', Icon: Undo2 },
  transfer: { label: 'Transfer', className: 'bg-surface-raised text-info', Icon: ArrowLeftRight },
}

function transactionTitle(transaction) {
  return (
    transaction.vendor ||
    transaction.description ||
    transaction.category?.name ||
    TYPE_META[transaction.type].label
  )
}

function transactionRoute(transaction) {
  if (transaction.type === 'transfer') {
    return `${transaction.account.name} to ${transaction.destination_account?.name ?? 'account'}`
  }
  return transaction.account.name
}

export default function Transactions() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)
  const [filterState, setFilterState] = useState({
    type: '',
    accountId: '',
    categoryId: '',
    dateFrom: '',
    dateTo: '',
  })
  const [page, setPage] = useState(1)
  const [modal, setModal] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const accountsQuery = useAccounts()
  const categoriesQuery = useCategories()
  const currenciesQuery = useCurrencies()
  const preferencesQuery = usePreferences()

  const accounts = accountsQuery.data ?? []
  const categories = categoriesQuery.data ?? []
  const currencies = currenciesQuery.data ?? []

  const setFilter = (key, value) => {
    setFilterState((current) => ({ ...current, [key]: value }))
    setPage(1)
  }

  const queryFilters = useMemo(() => {
    const filters = { page, page_size: 20 }
    if (deferredSearch.trim()) filters.search = deferredSearch.trim()
    if (filterState.type) filters.type = filterState.type
    if (filterState.accountId) filters.account_id = filterState.accountId
    if (filterState.categoryId) filters.category_id = filterState.categoryId
    if (filterState.dateFrom) filters.date_from = filterState.dateFrom
    if (filterState.dateTo) filters.date_to = filterState.dateTo
    return filters
  }, [page, deferredSearch, filterState])

  const transactionsQuery = useQuery({
    queryKey: ['transactions', queryFilters],
    queryFn: async () => {
      const response = await api.get('/transactions', { params: queryFilters })
      return response.data
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (transaction) => api.delete(`/transactions/${transaction.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      setDeleteTarget(null)
    },
  })

  const items = transactionsQuery.data?.data ?? []
  const meta = transactionsQuery.data?.meta ?? {
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
    totals: [],
  }
  const totals = meta.totals ?? []

  const decimalPlacesFor = (code) =>
    currencies.find((currency) => currency.code === code)?.decimal_places ?? 2

  const hasFilters =
    Boolean(deferredSearch.trim()) ||
    Object.values(filterState).some(Boolean)

  const clearFilters = () => {
    setSearch('')
    setFilterState({ type: '', accountId: '', categoryId: '', dateFrom: '', dateTo: '' })
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Transactions</h1>
          <p className="mt-1 text-sm text-text-muted">
            Income, spending, refunds and transfers. Transfers never count as income or spending.
          </p>
        </div>
        <Button
          onClick={() => setModal({ mode: 'create' })}
          disabled={accounts.length === 0}
          title={accounts.length === 0 ? 'Add an account first' : undefined}
        >
          <Plus size={16} aria-hidden="true" />
          Add transaction
        </Button>
      </div>

      {transactionsQuery.isError && (
        <Alert variant="error" title="Could not load transactions">
          {apiErrorMessage(transactionsQuery.error)}
        </Alert>
      )}

      {totals.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
          {totals.map((total) => (
            <section key={total.currency_code} className="card p-4" aria-label="Filtered totals">
              <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                Income
              </p>
              <p className="mt-1 text-lg font-semibold text-income">
                {formatMoney(
                  total.income_minor,
                  total.currency_code,
                  decimalPlacesFor(total.currency_code),
                )}
              </p>
              <p className="mt-2 text-xs text-text-muted">
                Spending{' '}
                <span className="font-medium text-expense">
                  {formatMoney(
                    total.spending_minor,
                    total.currency_code,
                    decimalPlacesFor(total.currency_code),
                  )}
                </span>
                {total.refunds_minor > 0 && (
                  <>
                    {' '}
                    · refunds{' '}
                    {formatMoney(
                      total.refunds_minor,
                      total.currency_code,
                      decimalPlacesFor(total.currency_code),
                    )}
                  </>
                )}
              </p>
              <p className="mt-1 text-xs text-text-muted">
                Net{' '}
                <span
                  className={`font-medium ${
                    total.net_minor < 0 ? 'text-expense' : 'text-income'
                  }`}
                >
                  {formatMoney(
                    total.net_minor,
                    total.currency_code,
                    decimalPlacesFor(total.currency_code),
                  )}
                </span>
              </p>
            </section>
          ))}
        </div>
      )}

      <section className="card p-4" aria-label="Transaction filters">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <div className="relative sm:col-span-2">
            <label htmlFor="transaction-search" className="sr-only">
              Search transactions
            </label>
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-2.5 text-text-muted"
              aria-hidden="true"
            />
            <input
              id="transaction-search"
              type="search"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
              placeholder="Search vendor, notes or category"
              className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-3 text-sm text-text placeholder:text-text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            />
          </div>

          <Select
            aria-label="Filter by type"
            value={filterState.type}
            onChange={(event) => setFilter('type', event.target.value)}
            placeholder="All types"
            options={Object.entries(TYPE_META).map(([value, entry]) => ({
              value,
              label: entry.label,
            }))}
          />

          <Select
            aria-label="Filter by account"
            value={filterState.accountId}
            onChange={(event) => setFilter('accountId', event.target.value)}
            placeholder="All accounts"
            options={accounts.map((account) => ({ value: account.id, label: account.name }))}
          />

          <Select
            aria-label="Filter by category"
            value={filterState.categoryId}
            onChange={(event) => setFilter('categoryId', event.target.value)}
            placeholder="All categories"
            options={categories.map((category) => ({
              value: category.id,
              label: category.name,
            }))}
          />

          <div className="flex gap-2">
            <Input
              aria-label="From date"
              type="date"
              value={filterState.dateFrom}
              onChange={(event) => setFilter('dateFrom', event.target.value)}
              className="flex-1"
            />
            <Input
              aria-label="To date"
              type="date"
              value={filterState.dateTo}
              onChange={(event) => setFilter('dateTo', event.target.value)}
              className="flex-1"
            />
          </div>
        </div>

        {hasFilters && (
          <button
            type="button"
            onClick={clearFilters}
            className="mt-3 text-xs font-medium text-primary hover:underline"
          >
            Clear filters
          </button>
        )}
      </section>

      {transactionsQuery.isLoading ? (
        <p className="text-sm text-text-muted">Loading transactions…</p>
      ) : items.length === 0 ? (
        <section className="card p-8 text-center">
          <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <ArrowLeftRight size={20} aria-hidden="true" />
          </span>
          <h2 className="mt-3 text-sm font-semibold text-text">
            {hasFilters ? 'No transactions match these filters' : 'No transactions yet'}
          </h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">
            {accounts.length === 0
              ? 'Add an account first, then record what you earn and spend.'
              : hasFilters
                ? 'Try a different search or clear the filters.'
                : 'Record your first transaction so your dashboard and reports have real data.'}
          </p>
          {accounts.length === 0 ? (
            <Link
              to="/accounts"
              className="mt-4 inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary transition-colors hover:opacity-90"
            >
              <Plus size={16} aria-hidden="true" />
              Add an account
            </Link>
          ) : (
            <Button className="mt-4" onClick={() => setModal({ mode: 'create' })}>
              <Plus size={16} aria-hidden="true" />
              Add transaction
            </Button>
          )}
        </section>
      ) : (
        <ul className="card divide-y divide-border" aria-label="Transactions">
          {items.map((transaction) => {
            const metaEntry = TYPE_META[transaction.type]
            const Icon = metaEntry.Icon
            const amountClass =
              transaction.type === 'expense'
                ? 'text-expense'
                : transaction.type === 'transfer'
                  ? 'text-text-muted'
                  : 'text-income'
            const prefix =
              transaction.type === 'expense' ? '−' : transaction.type === 'transfer' ? '' : '+'

            return (
              <li key={transaction.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-raised text-text-muted">
                  <Icon size={16} aria-hidden="true" />
                </span>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text">
                    {transactionTitle(transaction)}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-text-muted">
                    {formatDate(transaction.transaction_date)} · {transactionRoute(transaction)}
                    {transaction.category ? ` · ${transaction.category.name}` : ''}
                  </p>
                </div>

                <div className="text-right">
                  <p className={`text-sm font-semibold ${amountClass}`}>
                    {prefix}
                    {formatMoney(
                      transaction.amount_minor,
                      transaction.currency_code,
                      decimalPlacesFor(transaction.currency_code),
                    )}
                  </p>
                  <span className={`badge mt-1 ${metaEntry.className}`}>
                    {transaction.payment_method
                      ? titleCase(transaction.payment_method)
                      : metaEntry.label}
                  </span>
                </div>

                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => setModal({ mode: 'edit', transaction })}
                    aria-label={`Edit ${transactionTitle(transaction)}`}
                    className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
                  >
                    <Pencil size={15} aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(transaction)}
                    aria-label={`Delete ${transactionTitle(transaction)}`}
                    className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-expense"
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {meta.total_pages > 1 && (
        <nav className="flex items-center justify-between gap-3" aria-label="Pagination">
          <p className="text-xs text-text-muted">
            Page {meta.page} of {meta.total_pages} · {meta.total}{' '}
            {meta.total === 1 ? 'transaction' : 'transactions'}
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={meta.page <= 1 || transactionsQuery.isFetching}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((current) => current + 1)}
              disabled={meta.page >= meta.total_pages || transactionsQuery.isFetching}
            >
              Next
            </Button>
          </div>
        </nav>
      )}

      <Modal
        open={modal !== null}
        onClose={() => setModal(null)}
        title={modal?.mode === 'edit' ? 'Edit transaction' : 'Add transaction'}
        description="Amounts are stored to the cent; the type decides whether it adds or subtracts."
        size="lg"
      >
        {modal && (
          <TransactionForm
            key={modal.transaction?.id ?? 'new'}
            transaction={modal.transaction}
            accounts={accounts}
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
        title="Delete this transaction?"
        description="Deleted transactions are hidden everywhere but kept for audit."
        confirmLabel="Delete transaction"
        isPending={deleteMutation.isPending}
        errorMessage={deleteMutation.isError ? apiErrorMessage(deleteMutation.error) : null}
      />
    </div>
  )
}
