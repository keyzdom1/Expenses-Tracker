import { useEffect, useMemo, useState } from 'react'

import { supabase } from '../lib/supabase'
import { AuthContext } from './auth-context'

/**
 * Owns the Supabase session.
 *
 * Supabase stores the session and refreshes the token automatically. This
 * provider only mirrors that state into React and exposes the auth actions the
 * UI needs. Passwords never reach our API.
 */
export default function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(Boolean(supabase))

  useEffect(() => {
    if (!supabase) return undefined

    let active = true

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session ?? null)
      setLoading(false)
    })

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setLoading(false)
    })

    return () => {
      active = false
      subscription.subscription.unsubscribe()
    }
  }, [])

  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      loading,
      isConfigured: Boolean(supabase),

      async signIn(email, password) {
        if (!supabase) throw new Error('Supabase is not configured.')
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      },

      async signUp(email, password, fullName) {
        if (!supabase) throw new Error('Supabase is not configured.')
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { full_name: fullName },
            emailRedirectTo: `${window.location.origin}/login`,
          },
        })
        if (error) throw error
        return data
      },

      async signOut() {
        if (!supabase) return
        await supabase.auth.signOut()
      },

      async requestPasswordReset(email) {
        if (!supabase) throw new Error('Supabase is not configured.')
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        })
        if (error) throw error
      },

      async updatePassword(password) {
        if (!supabase) throw new Error('Supabase is not configured.')
        const { error } = await supabase.auth.updateUser({ password })
        if (error) throw error
      },
    }),
    [session, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
