import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Archive, CreditCard, Landmark, Pencil, Plus } from 'lucide-react'
import { useMemo, useState } from 'react'

import ConfirmDialog from '../components/ui/ConfirmDialog'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Modal from '../components/ui/Modal'
import Select from '../components/ui/Select'
import {
  useAccounts,
  useCurrencies,
  useDecimalPlaces,
  usePreferences,
} from '../hooks/useReferenceData'
import { api, apiErrorMessage } from '../lib/api'
import {
  formatMoney,
  minorToInput,
  parseSignedAmountInput,
  titleCase,
} from '../lib/format'

const ACCOUNT_TYPES = [
  'cash',
  'bank',
  'savings',
  'debit_card',
  'credit_card',
  'mobile_wallet',
]

const EMPTY_ACCOUNTS = []

function AccountForm({ account, currencies, defaultCurrency, onClose, onSaved }) {
  const queryClient = useQueryClient()
  const isEdit = Boolean(account)
  const [name, setName] = useState(account?.name ?? '')
  const [type, setType] = useState(account?.type ?? 'cash')
  const [currency, setCurrency] = useState(account?.currency_code ?? defaultCurrency)
  const [opening, setOpening] = useState(() =>
    account ? minorToInput(account.opening_balance_minor, 2) : '',
  )
  const [error, setError] = useState('')

  const decimalPlaces = useDecimalPlaces(currency, currencies)

  const mutation = useMutation({
    mutationFn: (payload) =>
      isEdit
        ? api.patch(`/accounts/${account.id}`, payload)
        : api.post('/accounts', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      onSaved()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError)),
  })

  const handleSubmit = (event) => {
    event.preventDefault()
    setError('')

    if (!name.trim()) {
      setError('Give the account a name.')
      return
    }

    const openingMinor = opening.trim() === '' ? 0 : parseSignedAmountInput(opening, decimalPlaces)
    if (openingMinor === null) {
      setError('Enter a valid opening balance, or leave it empty for zero.')
      return
    }

    const payload = {
      name: name.trim(),
      type,
      opening_balance_minor: openingMinor,
    }
    if (!isEdit) payload.currency_code = currency

    mutation.mutate(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <Alert variant="error">{error}</Alert>}

      <Input
        label="Account name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="GTBank current account"
        maxLength={120}
        required
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Account type"
          value={type}
          onChange={(event) => setType(event.target.value)}
          options={ACCOUNT_TYPES.map((value) => ({ value, label: titleCase(value) }))}
        />

        {isEdit ? (
          <Input label="Currency" value={currency} disabled readOnly hint="Currency is fixed." />
        ) : (
          <Select
            label="Currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value)}
            options={currencies.map((option) => ({
              value: option.code,
              label: `${option.code} - ${option.name}`,
            }))}
          />
        )}
      </div>

      <Input
        label="Opening balance"
        value={opening}
        onChange={(event) => setOpening(event.target.value)}
        inputMode="decimal"
        placeholder="0.00"
        hint={
          type === 'credit_card'
            ? 'For a credit card, enter what you already owe as a negative amount.'
            : 'The balance before any transactions you record here.'
        }
      />

      <div className="flex justify-end gap-2 pt-1">
        <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button type="submit" isLoading={mutation.isPending}>
          {isEdit ? 'Save account' : 'Create account'}
        </Button>
      </div>
    </form>
  )
}

export default function Accounts() {
  const queryClient = useQueryClient()
  const [includeArchived, setIncludeArchived] = useState(false)
  const [modal, setModal] = useState(null)
  const [archiveTarget, setArchiveTarget] = useState(null)

  const accountsQuery = useAccounts({ includeArchived })
  const preferencesQuery = usePreferences()
  const currenciesQuery = useCurrencies()

  const currencies = currenciesQuery.data ?? []
  const accounts = accountsQuery.data ?? EMPTY_ACCOUNTS

  const totals = useMemo(() => {
    const byCurrency = new Map()
    for (const account of accounts) {
      if (!account.is_active) continue
      const current = byCurrency.get(account.currency_code) ?? 0
      byCurrency.set(account.currency_code, current + account.balance_minor)
    }
    return [...byCurrency.entries()]
  }, [accounts])

  const archiveMutation = useMutation({
    mutationFn: (account) => api.delete(`/accounts/${account.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      setArchiveTarget(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Accounts</h1>
          <p className="mt-1 text-sm text-text-muted">
            Cash, bank, savings and card balances. Balances are derived from your transactions.
          </p>
        </div>
        <Button onClick={() => setModal({ mode: 'create' })}>
          <Plus size={16} aria-hidden="true" />
          Add account
        </Button>
      </div>

      {accountsQuery.isError && (
        <Alert variant="error" title="Could not load accounts">
          {apiErrorMessage(accountsQuery.error)}
        </Alert>
      )}

      {totals.length > 0 && (
        <section className="card flex flex-wrap items-center gap-x-8 gap-y-3 p-4" aria-label="Net worth">
          <span className="text-xs font-medium uppercase tracking-wide text-text-muted">
            Net worth
          </span>
          {totals.map(([currency, amount]) => (
            <span key={currency} className="text-lg font-semibold text-text">
              {formatMoney(amount, currency, 2)}
            </span>
          ))}
        </section>
      )}

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-text-muted">
          {accounts.length} {accounts.length === 1 ? 'account' : 'accounts'}
        </p>
        <label className="flex items-center gap-2 text-xs text-text-muted">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(event) => setIncludeArchived(event.target.checked)}
            className="h-4 w-4 rounded border-border text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          />
          Show archived
        </label>
      </div>

      {accountsQuery.isLoading ? (
        <p className="text-sm text-text-muted">Loading accounts…</p>
      ) : accounts.length === 0 ? (
        <section className="card p-8 text-center">
          <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Landmark size={20} aria-hidden="true" />
          </span>
          <h2 className="mt-3 text-sm font-semibold text-text">No accounts yet</h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">
            Add the account you spend from first. Every transaction is recorded against an account
            so balances always reconcile.
          </p>
          <Button className="mt-4" onClick={() => setModal({ mode: 'create' })}>
            <Plus size={16} aria-hidden="true" />
            Add your first account
          </Button>
        </section>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {accounts.map((account) => {
            const decimalPlaces = currencies.find(
              (currency) => currency.code === account.currency_code,
            )?.decimal_places
            return (
              <article
                key={account.id}
                className={`card p-5 ${account.is_active ? '' : 'opacity-60'}`}
                aria-label={account.name}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate text-sm font-semibold text-text">{account.name}</h2>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <span className="badge bg-surface-raised text-text-muted">
                        {account.type === 'credit_card' ? (
                          <CreditCard size={12} aria-hidden="true" />
                        ) : (
                          <Landmark size={12} aria-hidden="true" />
                        )}
                        {titleCase(account.type)}
                      </span>
                      <span className="badge bg-surface-raised text-text-muted">
                        {account.currency_code}
                      </span>
                      {!account.is_active && (
                        <span className="badge bg-warning-soft text-warning">Archived</span>
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 gap-1">
                    {account.is_active && (
                      <>
                        <button
                          type="button"
                          onClick={() => setModal({ mode: 'edit', account })}
                          aria-label={`Edit ${account.name}`}
                          className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-text"
                        >
                          <Pencil size={15} aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setArchiveTarget(account)}
                          aria-label={`Archive ${account.name}`}
                          className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-raised hover:text-expense"
                        >
                          <Archive size={15} aria-hidden="true" />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <p
                  className={`mt-4 text-2xl font-semibold tracking-tight ${
                    account.balance_minor < 0 ? 'text-expense' : 'text-text'
                  }`}
                >
                  {formatMoney(account.balance_minor, account.currency_code, decimalPlaces ?? 2)}
                </p>
                {account.type === 'credit_card' && (
                  <p className="mt-1 text-xs text-text-muted">
                    {account.balance_minor < 0 ? 'Amount owed' : 'Credit balance'}
                  </p>
                )}
              </article>
            )
          })}
        </div>
      )}

      <Modal
        open={modal !== null}
        onClose={() => setModal(null)}
        title={modal?.mode === 'edit' ? 'Edit account' : 'Add account'}
        description={
          modal?.mode === 'edit'
            ? 'Balances still come from your transactions; only the opening balance changes.'
            : 'Create an account before recording transactions against it.'
        }
      >
        {modal && (
          <AccountForm
            key={modal.account?.id ?? 'new'}
            account={modal.account}
            currencies={currencies}
            defaultCurrency={preferencesQuery.data?.currency_code ?? 'NGN'}
            onClose={() => setModal(null)}
            onSaved={() => setModal(null)}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={archiveTarget !== null}
        onClose={() => setArchiveTarget(null)}
        onConfirm={() => archiveMutation.mutate(archiveTarget)}
        title={`Archive ${archiveTarget?.name ?? 'account'}?`}
        description="Archived accounts keep their full history but cannot receive new transactions."
        confirmLabel="Archive account"
        isPending={archiveMutation.isPending}
        variant="secondary"
        errorMessage={
          archiveMutation.isError ? apiErrorMessage(archiveMutation.error) : null
        }
      />
    </div>
  )
}
