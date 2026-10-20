import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import ThemeProvider from '../../context/ThemeProvider'
import ThemeToggle from './ThemeToggle'

function renderToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  )
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  it('defaults to the system option', () => {
    renderToggle()

    expect(screen.getByRole('button', { name: 'System theme' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('applies dark mode and persists the choice', async () => {
    const user = userEvent.setup()
    renderToggle()

    await user.click(screen.getByRole('button', { name: 'Dark theme' }))

    expect(document.documentElement).toHaveClass('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(screen.getByRole('button', { name: 'Dark theme' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('switches back to light and clears the dark class', async () => {
    const user = userEvent.setup()
    renderToggle()

    await user.click(screen.getByRole('button', { name: 'Dark theme' }))
    await user.click(screen.getByRole('button', { name: 'Light theme' }))

    expect(document.documentElement).not.toHaveClass('dark')
    expect(localStorage.getItem('theme')).toBe('light')
  })

  it('removes the stored key when following the system again', async () => {
    const user = userEvent.setup()
    renderToggle()

    await user.click(screen.getByRole('button', { name: 'Dark theme' }))
    await user.click(screen.getByRole('button', { name: 'System theme' }))

    expect(localStorage.getItem('theme')).toBeNull()
  })
})
