import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Eye,
  Paperclip,
  Trash2,
  Undo2,
} from 'lucide-react'
import { useRef, useState } from 'react'

import Alert from '../ui/Alert'
import Button from '../ui/Button'
import ConfirmDialog from '../ui/ConfirmDialog'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Textarea from '../ui/Textarea'
import { api, apiErrorMessage } from '../../lib/api'
import { minorToInput, parseAmountInput, titleCase, todayISO } from '../../lib/format'

const MAX_RECEIPT_BYTES = 5 * 1024 * 1024

const TYPES = [
  { value: 'expense', label: 'Expense', Icon: ArrowUpRight },
  { value: 'income', label: 'Income', Icon: ArrowDownLeft },
  { value: 'refund', label: 'Refund', Icon: Undo2 },
  { value: 'transfer', label: 'Transfer', Icon: ArrowLeftRight },
]

const PAYMENT_METHODS = [
  'cash',
  'bank_transfer',
  'debit_card',
  'credit_card',
  'mobile_wallet',
  'other',
]

function kindForType(type) {
  return type === 'income' ? 'income' : 'expense'
}

export default function TransactionForm({
  transaction,
  accounts,
  categories,
  currencies,
  defaultCurrency,
  onClose,
  onSaved,
}) {
  const queryClient = useQueryClient()
  const isEdit = Boolean(transaction)
  const idempotencyKey = useRef(crypto.randomUUID())

  const [type, setType] = useState(transaction?.type ?? 'expense')
  const [accountId, setAccountId] = useState(
    transaction?.account.id ?? accounts[0]?.id ?? '',
  )
  const [destAccountId, setDestAccountId] = useState(
    transaction?.destination_account?.id ?? '',
  )
  const [categoryId, setCategoryId] = useState(transaction?.category?.id ?? '')
  const [amount, setAmount] = useState(() => {
    if (!transaction) return ''
    const currency = currencies.find(
      (row) => row.code === transaction.account.currency_code,
    )
    return minorToInput(transaction.amount_minor, currency?.decimal_places ?? 2)
  })
  const [transactionDate, setTransactionDate] = useState(
    transaction?.transaction_date ?? todayISO(),
  )
  const [paymentMethod, setPaymentMethod] = useState(transaction?.payment_method ?? '')
  const [vendor, setVendor] = useState(transaction?.vendor ?? '')
  const [description, setDescription] = useState(transaction?.description ?? '')
  const [refundOfId, setRefundOfId] = useState(transaction?.refund_of_id ?? '')
  const [error, setError] = useState('')
  const [receiptFile, setReceiptFile] = useState(null)
  const [receiptError, setReceiptError] = useState('')
  const [confirmReceiptDelete, setConfirmReceiptDelete] = useState(false)
  const receiptInput = useRef(null)

  const selectedAccount = accounts.find((account) => account.id === accountId)
  const currency = selectedAccount?.currency_code ?? defaultCurrency
  const decimalPlaces =
    currencies.find((row) => row.code === currency)?.decimal_places ?? 2

  const categoryKind = kindForType(type)
  const categoryOptions = categories
    .filter((category) => category.kind === categoryKind)
    .map((category) => {
      const parent = category.parent_id
        ? categories.find((row) => row.id === category.parent_id)
        : null
      return {
        value: category.id,
        label: parent ? `${parent.name} / ${category.name}` : category.name,
      }
    })

  const refundCandidates = useQuery({
    queryKey: ['refund-candidates', accountId],
    enabled: type === 'refund' && Boolean(accountId),
    queryFn: async () => {
      const response = await api.get('/transactions', {
        params: { type: 'expense', account_id: accountId, page_size: 50 },
      })
      return response.data.data
    },
  })

  const mutation = useMutation({
    mutationFn: (payload) =>
      isEdit
        ? api.patch(`/transactions/${transaction.id}`, payload)
        : api.post('/transactions', payload, {
            headers: { 'Idempotency-Key': idempotencyKey.current },
          }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['report-overview'] })
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      onSaved()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError)),
  })

  const receiptQuery = useQuery({
    queryKey: ['receipt', transaction?.id],
    enabled: isEdit,
    retry: false,
    queryFn: async () => {
      try {
        return (await api.get(`/transactions/${transaction.id}/receipt`)).data.data
      } catch (requestError) {
        if (requestError.response?.status === 404) return null
        throw requestError
      }
    },
  })

  const uploadReceipt = useMutation({
    mutationFn: (file) => {
      const formData = new FormData()
      formData.append('file', file)
      return api.post(`/transactions/${transaction.id}/receipt`, formData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['receipt', transaction.id] })
      setReceiptFile(null)
      if (receiptInput.current) receiptInput.current.value = ''
    },
    onError: (requestError) => setReceiptError(apiErrorMessage(requestError)),
  })

  const deleteReceipt = useMutation({
    mutationFn: () => api.delete(`/transactions/${transaction.id}/receipt`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['receipt', transaction.id] })
      setConfirmReceiptDelete(false)
    },
    onError: (requestError) => setReceiptError(apiErrorMessage(requestError)),
  })

  const viewReceipt = async () => {
    setReceiptError('')
    const popup = window.open('', '_blank', 'noopener,noreferrer')
    try {
      const response = await api.get(`/transactions/${transaction.id}/receipt/url`)
      if (popup) popup.location = response.data.data.url
    } catch (requestError) {
      if (popup) popup.close()
      setReceiptError(apiErrorMessage(requestError))
    }
  }

  const handleTypeChange = (nextType) => {
    setType(nextType)
    if (nextType !== 'refund') setRefundOfId('')

    if (nextType === 'transfer') {
      setCategoryId('')
      return
    }

    const selected = categories.find((category) => category.id === categoryId)
    if (selected && selected.kind !== kindForType(nextType)) setCategoryId('')
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    setError('')

    if (!accountId) {
      setError('Choose the account this transaction belongs to.')
      return
    }

    const amountMinor = parseAmountInput(amount, decimalPlaces)
    if (amountMinor === null || amountMinor <= 0) {
      setError('Enter an amount greater than zero.')
      return
    }

    if (type === 'transfer') {
      if (!destAccountId) {
        setError('Choose a destination account for the transfer.')
        return
      }
      if (destAccountId === accountId) {
        setError('Choose a different destination account.')
        return
      }
    }

    const payload = {
      type,
      amount_minor: amountMinor,
      account_id: accountId,
      transaction_date: transactionDate,
      payment_method: paymentMethod || null,
      vendor: vendor.trim() || null,
      description: description.trim() || null,
    }

    if (type === 'transfer') {
      payload.dest_account_id = destAccountId
    } else {
      payload.category_id = categoryId || null
      if (isEdit) payload.dest_account_id = null
    }

    if (type === 'refund') {
      payload.refund_of_id = refundOfId || null
    }

    mutation.mutate(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <Alert variant="error">{error}</Alert>}

      <fieldset>
        <legend className="mb-1.5 block text-xs font-medium text-text">Type</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {TYPES.map(({ value, label, Icon }) => (
            <button
              key={value}
              type="button"
              aria-pressed={type === value}
              onClick={() => handleTypeChange(value)}
              className={[
                'inline-flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-medium transition-colors',
                type === value
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-surface text-text-muted hover:bg-surface-raised hover:text-text',
              ].join(' ')}
            >
              <Icon size={14} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label={`Amount (${currency})`}
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          inputMode="decimal"
          placeholder="0.00"
          required
        />
        <Input
          label="Date"
          type="date"
          value={transactionDate}
          onChange={(event) => setTransactionDate(event.target.value)}
          required
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label={type === 'transfer' ? 'From account' : 'Account'}
          value={accountId}
          onChange={(event) => {
            setAccountId(event.target.value)
            if (event.target.value === destAccountId) setDestAccountId('')
          }}
          placeholder="Choose an account"
          options={accounts.map((account) => ({
            value: account.id,
            label: `${account.name} (${account.currency_code})`,
          }))}
        />

        {type === 'transfer' ? (
          <Select
            label="To account"
            value={destAccountId}
            onChange={(event) => setDestAccountId(event.target.value)}
            placeholder="Choose a destination"
            options={accounts
              .filter(
                (account) =>
                  account.id !== accountId && account.currency_code === currency,
              )
              .map((account) => ({ value: account.id, label: account.name }))}
            hint="Transfers stay within the same currency."
          />
        ) : (
          <Select
            label="Category"
            value={categoryId}
            onChange={(event) => setCategoryId(event.target.value)}
            placeholder="Uncategorised"
            options={categoryOptions}
          />
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Vendor or payee"
          value={vendor}
          onChange={(event) => setVendor(event.target.value)}
          maxLength={200}
          placeholder="Shoprite"
        />
        <Select
          label="Payment method"
          value={paymentMethod}
          onChange={(event) => setPaymentMethod(event.target.value)}
          placeholder="Not specified"
          options={PAYMENT_METHODS.map((value) => ({ value, label: titleCase(value) }))}
        />
      </div>

      {type === 'refund' && (
        <Select
          label="Refund for"
          value={refundOfId}
          onChange={(event) => setRefundOfId(event.target.value)}
          placeholder="Not linked to an expense"
          hint="Linking a refund reduces spending in that expense's category."
          options={(refundCandidates.data ?? [])
            .filter((candidate) => candidate.id !== transaction?.id)
            .map((candidate) => ({
              value: candidate.id,
              label: `${candidate.vendor || candidate.description || 'Expense'} - ${
                candidate.transaction_date
              }`,
            }))}
        />
      )}

      <Textarea
        label="Notes"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        rows={3}
        maxLength={2000}
        placeholder="Optional details"
      />

      {isEdit && (
        <fieldset className="rounded-xl border border-border p-3">
          <legend className="px-1 text-xs font-medium text-text">Receipt</legend>

          {receiptError && (
            <Alert variant="error" className="mb-3">
              {receiptError}
            </Alert>
          )}

          {receiptQuery.isLoading ? (
            <p className="text-xs text-text-muted">Checking for a receipt…</p>
          ) : receiptQuery.data ? (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <Paperclip size={15} className="shrink-0 text-text-muted" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium text-text">
                    {receiptQuery.data.file_name}
                  </p>
                  <p className="text-xs text-text-muted">
                    {(receiptQuery.data.size_bytes / 1024).toFixed(0)} KB ·{' '}
                    {receiptQuery.data.mime_type.split('/')[1].toUpperCase()}
                  </p>
                </div>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="secondary" onClick={viewReceipt}>
                  <Eye size={14} aria-hidden="true" />
                  View
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setConfirmReceiptDelete(true)}
                >
                  <Trash2 size={14} aria-hidden="true" />
                  Delete
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <input
                ref={receiptInput}
                type="file"
                accept=".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf"
                aria-label="Receipt file"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null
                  setReceiptError('')
                  if (file && file.size > MAX_RECEIPT_BYTES) {
                    setReceiptError('Receipts must be 5 MB or smaller.')
                    setReceiptFile(null)
                    event.target.value = ''
                    return
                  }
                  setReceiptFile(file)
                }}
                className="block w-full text-xs text-text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-surface-raised file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-text"
              />
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-text-muted">JPEG, PNG, WebP or PDF · up to 5 MB</p>
                <Button
                  size="sm"
                  onClick={() => uploadReceipt.mutate(receiptFile)}
                  isLoading={uploadReceipt.isPending}
                  disabled={!receiptFile}
                >
                  Upload receipt
                </Button>
              </div>
            </div>
          )}
        </fieldset>
      )}

      <div className="flex justify-end gap-2 pt-1">
        <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button type="submit" isLoading={mutation.isPending}>
          {isEdit ? 'Save transaction' : 'Add transaction'}
        </Button>
      </div>

      <ConfirmDialog
        open={confirmReceiptDelete}
        onClose={() => setConfirmReceiptDelete(false)}
        onConfirm={() => deleteReceipt.mutate()}
        title="Delete this receipt?"
        description="The file is removed from private storage. The transaction stays."
        confirmLabel="Delete receipt"
        isPending={deleteReceipt.isPending}
        errorMessage={
          deleteReceipt.isError ? apiErrorMessage(deleteReceipt.error) : null
        }
      />
    </form>
  )
}
