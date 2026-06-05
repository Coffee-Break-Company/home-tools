import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '@/components/ProtectedRoute'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '@/contexts/AuthContext'

function renderRoute(authState: object) {
  vi.mocked(useAuth).mockReturnValue({
    auth: authState as never,
    signInWithGoogle: vi.fn(),
    signOut: vi.fn(),
  })

  render(
    <MemoryRouter initialEntries={['/protected']}>
      <Routes>
        <Route
          path="/protected"
          element={<ProtectedRoute><div>conteúdo protegido</div></ProtectedRoute>}
        />
        <Route path="/login" element={<div>página de login</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows a spinner while auth is loading', () => {
    renderRoute({ status: 'loading' })
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    expect(screen.queryByText('conteúdo protegido')).not.toBeInTheDocument()
  })

  it('redirects to /login when unauthenticated', () => {
    renderRoute({ status: 'unauthenticated' })
    expect(screen.getByText('página de login')).toBeInTheDocument()
    expect(screen.queryByText('conteúdo protegido')).not.toBeInTheDocument()
  })

  it('redirects to /login when unauthorized', () => {
    renderRoute({ status: 'unauthorized', email: 'blocked@example.com' })
    expect(screen.getByText('página de login')).toBeInTheDocument()
  })

  it('renders children when authenticated', () => {
    renderRoute({ status: 'authenticated', user: {}, session: {} })
    expect(screen.getByText('conteúdo protegido')).toBeInTheDocument()
  })
})
