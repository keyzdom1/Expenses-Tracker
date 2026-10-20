import { useQuery } from '@tanstack/react-query'

import { api } from '../lib/api'

/** Accounts, optionally including archived ones. */
export function useAccounts({ includeArchived = false } = {}) {
  return useQuery({
    queryKey: ['accounts', { includeArchived }],
    queryFn: async () => {
      const response = await api.get('/accounts', {
        params: { include_archived: includeArchived },
      })
      return response.data.data
    },
  })
}

/** All categories for the signed-in user; defaults are seeded on first read. */
export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => (await api.get('/categories')).data.data,
  })
}

/** Profile preferences (currency, timezone, notification flags). */
export function usePreferences() {
  return useQuery({
    queryKey: ['preferences'],
    queryFn: async () => (await api.get('/me/preferences')).data.data,
  })
}

/** Supported currencies with their decimal precision. */
export function useCurrencies() {
  return useQuery({
    queryKey: ['currencies'],
    queryFn: async () => (await api.get('/currencies')).data.data,
    staleTime: Infinity,
  })
}

/** Budgets with live actuals for the current period. */
export function useBudgets() {
  return useQuery({
    queryKey: ['budgets'],
    queryFn: async () => (await api.get('/budgets')).data.data,
  })
}

/** Decimal places for a currency code, falling back to 2. */
export function useDecimalPlaces(currencyCode, currencies = []) {
  const match = currencies.find((currency) => currency.code === currencyCode)
  return match?.decimal_places ?? 2
}

/** Recurring templates; paused ones are excluded unless requested. */
export function useRecurring({ includeInactive = false } = {}) {
  return useQuery({
    queryKey: ['recurring', { includeInactive }],
    queryFn: async () =>
      (
        await api.get('/recurring', {
          params: { include_inactive: includeInactive },
        })
      ).data.data,
  })
}

/** Bill occurrences, optionally filtered by status and due date. */
export function useBills({ status = '', dueFrom = '', dueTo = '' } = {}) {
  return useQuery({
    queryKey: ['bills', { status, dueFrom, dueTo }],
    queryFn: async () =>
      (
        await api.get('/bills', {
          params: {
            ...(status ? { status } : {}),
            ...(dueFrom ? { due_from: dueFrom } : {}),
            ...(dueTo ? { due_to: dueTo } : {}),
          },
        })
      ).data.data,
  })
}

/** In-app notifications; polled so reminders appear without a reload. */
export function useNotifications({ limit = 20 } = {}) {
  return useQuery({
    queryKey: ['notifications', { limit }],
    queryFn: async () =>
      (await api.get('/notifications', { params: { limit } })).data,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
