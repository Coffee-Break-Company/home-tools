import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '@/App'

vi.mock('@/contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: vi.fn(),
}))

vi.mock('@/components/ProtectedRoute', () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/pages/Login', () => ({ Login: () => <div>login-page</div> }))
vi.mock('@/pages/Home', () => ({ Home: () => <div>home-page</div> }))
vi.mock('@/pages/Bills', () => ({ Bills: () => <div>bills-page</div>, iconForBill: vi.fn() }))

function renderAt(path: string) {
  render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe('App routing', () => {
  it('renders Home at /', () => {
    renderAt('/')
    expect(screen.getByText('home-page')).toBeInTheDocument()
  })

  it('renders Login at /login', () => {
    renderAt('/login')
    expect(screen.getByText('login-page')).toBeInTheDocument()
  })

  it('renders Bills at /contas', () => {
    renderAt('/contas')
    expect(screen.getByText('bills-page')).toBeInTheDocument()
  })

  it('redirects unknown paths to /', () => {
    renderAt('/unknown-path')
    expect(screen.getByText('home-page')).toBeInTheDocument()
  })
})
