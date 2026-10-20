import { createContext, useContext } from 'react'

/** Authentication context (split from the provider for Fast Refresh). */
export const AuthContext = createContext(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
