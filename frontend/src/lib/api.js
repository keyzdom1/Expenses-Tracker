import axios from 'axios'

import { supabase } from './supabase'

/** Backend origin, e.g. http://localhost:8000 - the client adds /api/v1. */
export const API_ORIGIN = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
).replace(/\/+$/, '')
export const API_V1 = `${API_ORIGIN}/api/v1`

export const api = axios.create({
  baseURL: API_V1,
  headers: { 'Content-Type': 'application/json' },
  timeout: 20000,
})

// Attach the current Supabase access token to every API request.
api.interceptors.request.use(async (config) => {
  if (supabase) {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise = null

/**
 * On 401, refresh the session exactly once and retry. If the refresh fails
 * (expired refresh token, revoked user) the user is signed out.
 */
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    if (status === 401 && original && !original._retry && supabase) {
      original._retry = true
      try {
        refreshPromise = refreshPromise ?? supabase.auth.refreshSession()
        const { data, error: refreshError } = await refreshPromise
        refreshPromise = null

        const token = data?.session?.access_token
        if (refreshError || !token) throw refreshError ?? new Error('Session refresh failed')

        original.headers = { ...original.headers, Authorization: `Bearer ${token}` }
        return api(original)
      } catch {
        refreshPromise = null
        await supabase.auth.signOut()
      }
    }

    return Promise.reject(error)
  },
)

/** Turn an Axios error into the backend's message, with sane fallbacks. */
export function apiErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const envelope = error?.response?.data?.error
  if (envelope?.message) return envelope.message
  if (error?.code === 'ERR_NETWORK') return 'Cannot reach the API. Is the backend running?'
  if (error?.response?.status === 401) return 'Your session has expired. Please sign in again.'
  if (error?.response?.status === 404) return 'That resource could not be found.'
  return fallback
}

/** GET /health (lives outside /api/v1). */
export async function fetchHealth() {
  const { data } = await axios.get(`${API_ORIGIN}/health`, { timeout: 8000 })
  return data.data
}
