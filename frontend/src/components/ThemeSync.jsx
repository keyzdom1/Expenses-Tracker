import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { useTheme } from '../context/theme-context'
import { api } from '../lib/api'

/**
 * Keeps the theme in sync with the user's saved preference so the choice
 * follows them across devices (Section 9.1, step 4).
 *
 * Rendered only inside authenticated routes, so it never fires before login.
 */
export default function ThemeSync() {
  const { theme, setTheme } = useTheme()
  const queryClient = useQueryClient()
  const hydrated = useRef(false)
  const lastSynced = useRef(null)

  const { data } = useQuery({
    queryKey: ['preferences'],
    queryFn: async () => (await api.get('/me/preferences')).data.data,
    staleTime: 5 * 60 * 1000,
  })

  // Adopt the server preference once, without echoing it straight back.
  useEffect(() => {
    if (!data || hydrated.current) return
    hydrated.current = true
    lastSynced.current = data.theme
    if (data.theme !== theme) setTheme(data.theme)
  }, [data, theme, setTheme])

  // Push later local changes back to the profile.
  useEffect(() => {
    if (!hydrated.current || lastSynced.current === theme) return
    lastSynced.current = theme
    api
      .patch('/me/preferences', { theme })
      .then(() => {
        queryClient.setQueryData(['preferences'], (previous) =>
          previous ? { ...previous, theme } : previous,
        )
      })
      .catch(() => {
        /* Keep the local choice if the sync fails; it will be retried next change. */
      })
  }, [theme, queryClient])

  return null
}
