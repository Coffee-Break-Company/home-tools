import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importActual) => {
  const actual = await importActual<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

import { Login } from '@/pages/Login'
import { useAuth } from '@/contexts/AuthContext'

function renderLogin(status: string, email?: string) {
  const signInWithGoogle = vi.fn()
  vi.mocked(useAuth).mockReturnValue({
    auth: (email ? { status, email } : { status }) as never,
    signInWithGoogle,
    signOut: vi.fn(),
  })
  render(<MemoryRouter><Login /></MemoryRouter>)
  return { signInWithGoogle }
}

describe('Login', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the Google sign-in button', () => {
    renderLogin('unauthenticated')
    expect(screen.getByRole('button', { name: /entrar com google/i })).toBeInTheDocument()
  })

  it('navigates to / when already authenticated', () => {
    renderLogin('authenticated')
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
  })

  it('shows unauthorized message with the blocked email', () => {
    renderLogin('unauthorized', 'blocked@example.com')
    expect(screen.getByText(/acesso negado/i)).toBeInTheDocument()
    expect(screen.getByText('blocked@example.com')).toBeInTheDocument()
  })

  it('does not show unauthorized message when unauthenticated', () => {
    renderLogin('unauthenticated')
    expect(screen.queryByText(/acesso negado/i)).not.toBeInTheDocument()
  })

  it('calls signInWithGoogle when the button is clicked', async () => {
    const { signInWithGoogle } = renderLogin('unauthenticated')
    await userEvent.click(screen.getByRole('button', { name: /entrar com google/i }))
    expect(signInWithGoogle).toHaveBeenCalled()
  })
})
