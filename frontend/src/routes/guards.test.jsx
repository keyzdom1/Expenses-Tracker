import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { AuthContext } from '../context/auth-context'
import { ProtectedRoute } from './guards'

function renderRoute(authValue) {
  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={['/private']}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/private" element={<div>Private content</div>} />
          </Route>
          <Route path="/login" element={<div>Login screen</div>} />
          <Route path="/setup" element={<div>Setup screen</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

const baseAuth = {
  session: null,
  user: null,
  loading: false,
  isConfigured: true,
}

describe('ProtectedRoute', () => {
  it('redirects to login when there is no session', () => {
    renderRoute(baseAuth)

    expect(screen.getByText('Login screen')).toBeInTheDocument()
  })

  it('renders the protected page for a signed-in user', () => {
    renderRoute({ ...baseAuth, session: { access_token: 'token' } })

    expect(screen.getByText('Private content')).toBeInTheDocument()
  })

  it('shows a loading state while the session is resolving', () => {
    renderRoute({ ...baseAuth, loading: true })

    expect(screen.getByRole('status')).toHaveTextContent('Loading your session')
  })

  it('sends the user to setup when Supabase is not configured', () => {
    renderRoute({ ...baseAuth, isConfigured: false })

    expect(screen.getByText('Setup screen')).toBeInTheDocument()
  })
})
