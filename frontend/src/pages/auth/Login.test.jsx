import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AuthContext } from '../../context/auth-context'
import ThemeProvider from '../../context/ThemeProvider'
import Login from './Login'

function renderLogin(signIn) {
  return render(
    <ThemeProvider>
      <AuthContext.Provider
        value={{ session: null, user: null, loading: false, isConfigured: true, signIn }}
      >
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<div>Dashboard screen</div>} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeProvider>,
  )
}

describe('Login', () => {
  it('blocks submission and shows validation messages when empty', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn()
    renderLogin(signIn)

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Enter your email address.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
    expect(signIn).not.toHaveBeenCalled()
  })

  it('rejects an invalid email format', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn()
    renderLogin(signIn)

    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(signIn).not.toHaveBeenCalled()
  })

  it('signs in and navigates to the dashboard', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockResolvedValue(undefined)
    renderLogin(signIn)

    await user.type(screen.getByLabelText('Email'), 'ada@example.com')
    await user.type(screen.getByLabelText('Password'), 'secret123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(signIn).toHaveBeenCalledWith('ada@example.com', 'secret123')
    expect(await screen.findByText('Dashboard screen')).toBeInTheDocument()
  })

  it('shows the provider error when sign-in fails', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockRejectedValue(new Error('Invalid login credentials'))
    renderLogin(signIn)

    await user.type(screen.getByLabelText('Email'), 'ada@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrongpass')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid login credentials')
  })
})
