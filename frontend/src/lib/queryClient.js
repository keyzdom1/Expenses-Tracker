import { QueryClient } from '@tanstack/react-query'

/**
 * Shared React Query client.
 * Financial data changes on the server, so we keep stale time short and
 * refetch on window focus for the dashboard.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: 0,
    },
  },
})
