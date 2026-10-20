import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../context/auth-context'

function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg" role="status">
      <span className="text-sm text-text-muted">Loading your session…</span>
    </div>
  )
}

/** Requires a signed-in user; remembers where they were heading. */
export function ProtectedRoute() {
  const { session, loading, isConfigured } = useAuth()
  const location = useLocation()

  if (!isConfigured) return <Navigate to="/setup" replace />
  if (loading) return <FullPageLoader />
  if (!session) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

/** Keeps signed-in users away from the login/register screens. */
export function PublicOnlyRoute() {
  const { session, loading, isConfigured } = useAuth()

  if (!isConfigured) return <Navigate to="/setup" replace />
  if (loading) return <FullPageLoader />
  if (session) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
