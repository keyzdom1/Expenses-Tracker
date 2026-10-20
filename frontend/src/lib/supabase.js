import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

/**
 * Browser Supabase client. Only the public anon key is used here - the
 * service-role key must never reach the frontend.
 *
 * `null` means the project has not been configured yet; the UI shows a setup
 * notice instead of crashing.
 */
export const supabase = url && anonKey ? createClient(url, anonKey) : null

export const isSupabaseConfigured = Boolean(supabase)

export async function getAccessToken() {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
