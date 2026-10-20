import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import Alert from '../ui/Alert'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Textarea from '../ui/Textarea'
import { api, apiErrorMessage } from '../../lib/api'
import { minorToInput, parseAmountInput, titleCase, todayISO } from '../../lib/format'

const TYPES = ['expense', 'income', 'refund', 'transfer']
const FREQUENCIES = ['daily', 'weekly', 'monthly', 'yearly']
const PAYMENT_METHODS = [
  'cash',
  'bank_transfer',
  'debit_card',
  'credit_card',
  'mobile_wallet',
  'other',
]

export default function RecurringForm({ recurring, accounts, categories, currencies, onClose, onSaved }) {
  const queryClient = useQueryClient()
  const isEdit = Boolean(recurring)

  const [type, setType] = useState(recurring?.type ?? 'expense')
  const [amount, setAmount] = useState(() => {
    if (!recurring) return ''
    const currency = currencies.find((row) => row.code === recurring.currency_code)
    return minorToInput(recurring.amount_minor, currency?.decimal_places ?? 2)
  })
  const [accountId, setAccountId] = useState(
    recurring?.account?.id ?? accounts[0]?.id ?? '',
  )
  const [destAccountId, setDestAccountId] = useState(recurring?.destination_account?.id ?? '')
  const [categoryId, setCategoryId] = useState(recurring?.category?.id ?? '')
  const [paymentMethod, setPaymentMethod] = useState(recurring?.payment_method ?? '')
  const [vendor, setVendor] = useState(recurring?.vendor ?? '')
  const [description, setDescription] = useState(recurring?.description ?? '')
  const [frequency, setFrequency] = useState(recurring?.frequency ?? 'monthly')
  const [intervalCount, setIntervalCount] = useState(String(recurring?.interval_count ?? 1))
  const [startDate, setStartDate] = useState(recurring?.start_date ?? todayISO())
  const [endDate, setEndDate] = useState(recurring?.end_date ?? '')
  const [reminderDays, setReminderDays] = useState(String(recurring?.reminder_days ?? 3))
  const [error, setError] = useState('')

  const selectedAccount = accounts.find((row) => row.id === accountId)
  const accountCurrency = selectedAccount?.currency_code ?? recurring?.currency_code ?? 'NGN'
  const decimalPlaces =
    currencies.find((row) => row.code === accountCurrency)?.decimal_places ?? 2

  const categoryKind = type === 'income' ? 'income' : 'expense'
  const matchingCategories = categories.filter((row) => row.kind === categoryKind)
  const categoryOptions = matchingCategories.map((row) => {
    const parent = row.parent_id
      ? matchingCategories.find((candidate) => candidate.id === row.parent_id)
      : null
    return { value: row.id, label: parent ? `${parent.name} / ${row.name}` : row.name }
  })

  const mutation = useMutation({
    mutationFn: (payload) =>
      isEdit ? api.patch(`/recurring/${recurring.id}`, payload) : api.post('/recurring', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      onSaved()
    },
    onError: (requestError) => setError(apiErrorMessage(requestError)),
  })

  const changeType = (value) => {
    setType(value)
    if (value === 'transfer') {
      setCategoryId('')
      setPaymentMethod('')
    } else if (value === 'income') {
      if (categories.find((row) => row.id === categoryId)?.kind !== 'income') setCategoryId('')
    } else if (categories.find((row) => row.id === categoryId)?.kind !== 'expense') {
      setCategoryId('')
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    setError('')

    if (!accountId) {
      setError('Choose the account this will be paid from.')
      return
    }

    const amountMinor = parseAmountInput(amount, decimalPlaces)
    if (amountMinor === null || amountMinor <= 0) {
      setError('Enter an amount greater than zero, using at most the currency precision.')
      return
    }

    if (type === 'transfer') {
      if (!destAccountId) {
        setError('A transfer needs a destination account.')
        return
      }
      if (destAccountId === accountId) {
        setError('Choose two different accounts for a transfer.')
        return
      }
    }

    if (!startDate) {
      setError('Choose a start date.')
      return
    }
    if (endDate && endDate < startDate) {
      setError('The end date must be on or after the start date.')
      return
    }

    const interval = Number(intervalCount)
    if (!Number.isInteger(interval) || interval < 1 || interval > 12) {
      setError('Repeat every 1 to 12 intervals.')
      return
    }

    const reminder = Number(reminderDays)
    if (!Number.isInteger(reminder) || reminder < 0 || reminder > 30) {
      setError('Remind between 0 and 30 days before the bill is due.')
      return
    }

    mutation.mutate({
      type,
      amount_minor: amountMinor,
      account_id: accountId,
      dest_account_id: type === 'transfer' ? destAccountId : null,
      category_id: type === 'transfer' ? null : categoryId || null,
      payment_method: type === 'transfer' ? null : paymentMethod || null,
      vendor: vendor.trim() || null,
      description: description.trim() || null,
      frequency,
      interval_count: interval,
      start_date: startDate,
      end_date: endDate || null,
      reminder_days: reminder,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <Alert variant="error">{error}</Alert>}

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Type"
          value={type}
          onChange={(event) => changeType(event.target.value)}
          options={TYPES.map((value) => ({ value, label: titleCase(value) }))}
          hint="Transfers are never counted as spending."
        />
        <Input
          label={`Amount (${accountCurrency})`}
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          inputMode="decimal"
          placeholder="0.00"
          required
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label={type === 'income' ? 'Paid into' : 'Paid from'}
          value={accountId}
          onChange={(event) => setAccountId(event.target.value)}
          placeholder={accounts.length ? undefined : 'Add an account first'}
          options={accounts.map((row) => ({ value: row.id, label: row.name }))}
          required
        />
        {type === 'transfer' ? (
          <Select
            label="Destination account"
            value={destAccountId}
            onChange={(event) => setDestAccountId(event.target.value)}
            placeholder="Choose an account"
            options={accounts
              .filter((row) => row.id !== accountId)
              .map((row) => ({ value: row.id, label: row.name }))}
            required
          />
        ) : (
          <Select
            label="Category"
            value={categoryId}
            onChange={(event) => setCategoryId(event.target.value)}
            placeholder="Optional"
            options={categoryOptions}
          />
        )}
      </div>

      {type !== 'transfer' && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Payment method"
            value={paymentMethod}
            onChange={(event) => setPaymentMethod(event.target.value)}
            placeholder="Optional"
            options={PAYMENT_METHODS.map((value) => ({ value, label: titleCase(value) }))}
          />
          <Input
            label="Vendor or payee"
            value={vendor}
            onChange={(event) => setVendor(event.target.value)}
            placeholder="e.g. Netflix"
            maxLength={200}
          />
        </div>
      )}

      <Textarea
        label="Description"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        placeholder="Optional note"
        maxLength={2000}
        rows={2}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Select
          label="Frequency"
          value={frequency}
          onChange={(event) => setFrequency(event.target.value)}
          options={FREQUENCIES.map((value) => ({ value, label: titleCase(value) }))}
        />
        <Input
          label="Repeat every"
          type="number"
          min="1"
          max="12"
          value={intervalCount}
          onChange={(event) => setIntervalCount(event.target.value)}
          hint={`Every ${intervalCount || 1} ${frequency}${Number(intervalCount) === 1 ? '' : 's'}.`}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
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
          hint="Optional."
        />
        <Input
          label="Remind days before"
          type="number"
          min="0"
          max="30"
          value={reminderDays}
          onChange={(event) => setReminderDays(event.target.value)}
        />
      </div>

      <div className="flex justify-end gap-2 pt-1">
        <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        <Button type="submit" isLoading={mutation.isPending}>
          {isEdit ? 'Save template' : 'Create template'}
        </Button>
      </div>
    </form>
  )
}
