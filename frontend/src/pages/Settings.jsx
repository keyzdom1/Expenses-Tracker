import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, LogOut, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import ThemeToggle from '../components/layout/ThemeToggle'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Modal from '../components/ui/Modal'
import { useAuth } from '../context/auth-context'
import { api, apiErrorMessage } from '../lib/api'
import { filenameFromDisposition } from '../lib/reports'

const FALLBACK_ZONES = [
  'UTC',
  'Africa/Lagos',
  'Africa/Accra',
  'Africa/Nairobi',
  'Africa/Johannesburg',
  'Europe/London',
  'Europe/Paris',
  'America/New_York',
  'America/Los_Angeles',
  'Asia/Dubai',
]

function Section({ title, description, children }) {
  return (
    <section className="card p-5 sm:p-6" aria-label={title}>
      <h2 className="text-sm font-semibold text-text">{title}</h2>
      {description && <p className="mt-1 text-xs text-text-muted">{description}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

/** Mounted only after the profile loads, so initial state needs no effect. */
function ProfileForm({ profile, email, onSave, isSaving }) {
  const [fullName, setFullName] = useState(profile.full_name ?? '')

  return (
    <form
      className="max-w-md space-y-4"
      onSubmit={(event) => {
        event.preventDefault()
        onSave({ full_name: fullName.trim() || null })
      }}
    >
      <Input
        label="Full name"
        value={fullName}
        onChange={(event) => setFullName(event.target.value)}
        maxLength={120}
        autoComplete="name"
        placeholder="Ada Lovelace"
      />

      <Input
        label="Email"
        value={email ?? ''}
        readOnly
        disabled
        hint="Managed by your sign-in provider."
      />

      <Button type="submit" isLoading={isSaving}>
        Save profile
      </Button>
    </form>
  )
}

/** Mounted only after preferences load, so initial state needs no effect. */
function PreferencesForm({ preferences, currencies, timezones, onSave, isSaving }) {
  const [currency, setCurrency] = useState(preferences.currency_code)
  const [timezone, setTimezone] = useState(preferences.timezone)
  const [notifyBudget, setNotifyBudget] = useState(preferences.notify_budget_thresholds)
  const [notifyBills, setNotifyBills] = useState(preferences.notify_upcoming_bills)
  const [notifyRecurring, setNotifyRecurring] = useState(preferences.notify_recurring_events)

  const dirty =
    currency !== preferences.currency_code ||
    timezone !== preferences.timezone ||
    notifyBudget !== preferences.notify_budget_thresholds ||
    notifyBills !== preferences.notify_upcoming_bills ||
    notifyRecurring !== preferences.notify_recurring_events

  return (
    <form
      className="grid max-w-2xl gap-4 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSave({
          currency_code: currency,
          timezone,
          notify_budget_thresholds: notifyBudget,
          notify_upcoming_bills: notifyBills,
          notify_recurring_events: notifyRecurring,
        })
      }}
    >
      <div>
        <label htmlFor="currency" className="mb-1.5 block text-xs font-medium text-text">
          Currency
        </label>
        <select
          id="currency"
          value={currency}
          onChange={(event) => setCurrency(event.target.value)}
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          {currencies.map((option) => (
            <option key={option.code} value={option.code}>
              {option.code} - {option.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="timezone" className="mb-1.5 block text-xs font-medium text-text">
          Timezone
        </label>
        <select
          id="timezone"
          value={timezone}
          onChange={(event) => setTimezone(event.target.value)}
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          {timezones.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
      </div>

      <fieldset className="space-y-2 sm:col-span-2">
        <legend className="mb-1.5 text-xs font-medium text-text">In-app alerts</legend>

        <label className="flex items-start gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={notifyBudget}
            onChange={(event) => setNotifyBudget(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
          />
          <span>
            Budget thresholds
            <span className="block text-xs text-text-muted">
              Tell me when spending reaches the warning or critical limit.
            </span>
          </span>
        </label>

        <label className="flex items-start gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={notifyBills}
            onChange={(event) => setNotifyBills(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
          />
          <span>
            Upcoming and overdue bills
            <span className="block text-xs text-text-muted">
              Remind me within each template&apos;s reminder window.
            </span>
          </span>
        </label>

        <label className="flex items-start gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={notifyRecurring}
            onChange={(event) => setNotifyRecurring(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
          />
          <span>
            Recurring activity
            <span className="block text-xs text-text-muted">
              Occasional updates about recurring templates.
            </span>
          </span>
        </label>
      </fieldset>

      <div className="sm:col-span-2">
        <Button type="submit" isLoading={isSaving} disabled={!dirty}>
          Save preferences
        </Button>
      </div>
    </form>
  )
}

export default function Settings() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState(null)

  const profileQuery = useQuery({
    queryKey: ['me'],
    queryFn: async () => (await api.get('/me')).data.data,
  })
  const preferencesQuery = useQuery({
    queryKey: ['preferences'],
    queryFn: async () => (await api.get('/me/preferences')).data.data,
  })
  const currenciesQuery = useQuery({
    queryKey: ['currencies'],
    queryFn: async () => (await api.get('/currencies')).data.data,
    staleTime: Infinity,
  })

  const timezones = useMemo(() => {
    const supported =
      typeof Intl.supportedValuesOf === 'function'
        ? Intl.supportedValuesOf('timeZone')
        : FALLBACK_ZONES
    return supported.includes('Africa/Lagos') ? supported : ['Africa/Lagos', ...supported]
  }, [])

  const saveProfile = useMutation({
    mutationFn: (payload) => api.patch('/me', payload),
    onSuccess: (response) => {
      queryClient.setQueryData(['me'], response.data.data)
      setNotice({ variant: 'success', title: 'Profile saved' })
    },
    onError: (error) =>
      setNotice({ variant: 'error', title: 'Could not save profile', body: apiErrorMessage(error) }),
  })

  const savePreferences = useMutation({
    mutationFn: (payload) => api.patch('/me/preferences', payload),
    onSuccess: (response) => {
      queryClient.setQueryData(['preferences'], response.data.data)
      setNotice({ variant: 'success', title: 'Preferences saved' })
    },
    onError: (error) =>
      setNotice({
        variant: 'error',
        title: 'Could not save preferences',
        body: apiErrorMessage(error),
      }),
  })

  const [deleteOpen, setDeleteOpen] = useState(false)
  const [confirmText, setConfirmText] = useState('')

  const exportMutation = useMutation({
    mutationFn: async () => {
      const response = await api.get('/me/export', { responseType: 'blob' })
      const filename = filenameFromDisposition(
        response.headers['content-disposition'],
        'expense-tracker-export.json',
      )
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
    onSuccess: (filename) => {
      setNotice({
        variant: 'success',
        title: 'Your data was downloaded',
        body: filename,
      })
    },
    onError: (error) =>
      setNotice({
        variant: 'error',
        title: 'Could not export your data',
        body: apiErrorMessage(error, 'The export could not be downloaded. Try again.'),
      }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.delete('/me', { data: { confirm: confirmText } }),
    onSuccess: async () => {
      setDeleteOpen(false)
      setConfirmText('')
      queryClient.clear()
      await signOut()
      navigate('/login', { replace: true })
    },
    onError: (error) =>
      setNotice({
        variant: 'error',
        title: 'Could not delete your account',
        body: apiErrorMessage(error, 'Nothing was deleted. Please try again.'),
      }),
  })

  const closeDeleteDialog = () => {
    if (deleteMutation.isPending) return
    setDeleteOpen(false)
    setConfirmText('')
    deleteMutation.reset()
  }

  const handleSignOut = async () => {
    await signOut()
    navigate('/login', { replace: true })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-text">Settings</h1>
        <p className="mt-1 text-sm text-text-muted">
          Your profile, currency, timezone and theme are stored with your account.
        </p>
      </div>

      {notice && (
        <Alert variant={notice.variant} title={notice.title}>
          {notice.body}
        </Alert>
      )}

      <Section title="Profile" description="How your name appears in the app.">
        {profileQuery.isLoading ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : profileQuery.data ? (
          <ProfileForm
            profile={profileQuery.data}
            email={user?.email}
            isSaving={saveProfile.isPending}
            onSave={(payload) => {
              setNotice(null)
              saveProfile.mutate(payload)
            }}
          />
        ) : (
          <Alert variant="error">{apiErrorMessage(profileQuery.error)}</Alert>
        )}
      </Section>

      <Section
        title="Preferences"
        description="Used to format money and to decide which day a transaction belongs to."
      >
        {preferencesQuery.isLoading ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : preferencesQuery.data ? (
          <PreferencesForm
            preferences={preferencesQuery.data}
            currencies={currenciesQuery.data ?? []}
            timezones={timezones}
            isSaving={savePreferences.isPending}
            onSave={(payload) => {
              setNotice(null)
              savePreferences.mutate(payload)
            }}
          />
        ) : (
          <Alert variant="error">{apiErrorMessage(preferencesQuery.error)}</Alert>
        )}
      </Section>

      <Section title="Appearance" description="Applies immediately and follows you across devices.">
        <ThemeToggle />
      </Section>

      <Section
        title="Your data"
        description="Download a JSON copy of your profile, accounts, transactions, budgets, receipts metadata and other records."
      >
        <Button
          variant="secondary"
          onClick={() => {
            setNotice(null)
            exportMutation.mutate()
          }}
          isLoading={exportMutation.isPending}
        >
          <Download size={15} aria-hidden="true" />
          Download all data
        </Button>
        <p className="mt-2 text-xs text-text-muted">
          Receipt images stay in private storage; the export lists their metadata and storage references.
        </p>
      </Section>

      <Section
        title="Danger zone"
        description="Deleting your account removes every record we hold for you. This cannot be undone."
      >
        <Button variant="danger" onClick={() => setDeleteOpen(true)}>
          <Trash2 size={15} aria-hidden="true" />
          Delete account
        </Button>
      </Section>

      <Section title="Session" description="Signing out clears the session on this device.">
        <Button variant="secondary" onClick={handleSignOut}>
          <LogOut size={15} aria-hidden="true" />
          Sign out
        </Button>
      </Section>

      <Modal
        open={deleteOpen}
        onClose={closeDeleteDialog}
        title="Delete your account?"
        description="All accounts, transactions, budgets, bills and notifications will be permanently removed."
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={closeDeleteDialog} disabled={deleteMutation.isPending}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => deleteMutation.mutate()}
              isLoading={deleteMutation.isPending}
              disabled={confirmText !== 'DELETE'}
            >
              Delete everything
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <Alert variant="warning" title="This cannot be undone">
            Export your data first if you may need it later.
          </Alert>

          <Input
            label="Type DELETE to confirm"
            value={confirmText}
            onChange={(event) => setConfirmText(event.target.value)}
            autoComplete="off"
            placeholder="DELETE"
          />

          {deleteMutation.isError && (
            <Alert variant="error" title="Account not deleted">
              {apiErrorMessage(deleteMutation.error)}
            </Alert>
          )}
        </div>
      </Modal>
    </div>
  )
}
