import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(),
      signInWithOAuth: vi.fn(),
      signOut: vi.fn(),
    },
  },
}))

import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { supabase } from '@/lib/supabase'

const mockSession = {
  access_token: 'token-123',
  user: {
    id: 'user-1',
    email: 'test@example.com',
    app_metadata: {},
    user_metadata: {},
    aud: 'authenticated',
    created_at: '2024-01-01',
  },
}

function setupSupabaseMocks(session: typeof mockSession | null) {
  vi.mocked(supabase.auth.getSession).mockResolvedValue({
    data: { session: session as never },
    error: null,
  })
  vi.mocked(supabase.auth.onAuthStateChange).mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  } as never)
  vi.mocked(supabase.auth.signOut).mockResolvedValue({ error: null })
  vi.mocked(supabase.auth.signInWithOAuth).mockResolvedValue({ data: null, error: null } as never)
}

function StatusReader() {
  const { auth, signInWithGoogle, signOut } = useAuth()
  return (
    <div>
      <span data-testid="status">{auth.status}</span>
      {'email' in auth && <span data-testid="email">{auth.email}</span>}
      <button onClick={signInWithGoogle}>sign-in</button>
      <button onClick={signOut}>sign-out</button>
    </div>
  )
}

describe('AuthProvider / resolveAuth', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('fetch', mockFetch)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts in loading state before session resolves', () => {
    vi.mocked(supabase.auth.getSession).mockReturnValue(new Promise(() => {}))
    vi.mocked(supabase.auth.onAuthStateChange).mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    } as never)

    render(<AuthProvider><StatusReader /></AuthProvider>)

    expect(screen.getByTestId('status')).toHaveTextContent('loading')
  })

  it('sets unauthenticated when there is no session', async () => {
    setupSupabaseMocks(null)

    render(<AuthProvider><StatusReader /></AuthProvider>)

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'),
    )
  })

  it('sets authenticated when session is valid (200)', async () => {
    setupSupabaseMocks(mockSession)
    mockFetch.mockResolvedValue({ ok: true, status: 200 })

    render(<AuthProvider><StatusReader /></AuthProvider>)

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('authenticated'),
    )
  })

  it('sets unauthorized on 403 and signs out', async () => {
    setupSupabaseMocks(mockSession)
    mockFetch.mockResolvedValue({ ok: false, status: 403 })

    render(<AuthProvider><StatusReader /></AuthProvider>)

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('unauthorized'),
    )
    expect(screen.getByTestId('email')).toHaveTextContent('test@example.com')
    expect(supabase.auth.signOut).toHaveBeenCalled()
  })

  it('uses empty string as email fallback when user.email is undefined', async () => {
    const sessionNoEmail = { ...mockSession, user: { ...mockSession.user, email: undefined } }
    setupSupabaseMocks(sessionNoEmail as never)
    mockFetch.mockResolvedValue({ ok: false, status: 403 })

    render(<AuthProvider><StatusReader /></AuthProvider>)

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('unauthorized'),
    )
    expect(screen.getByTestId('email')).toHaveTextContent('')
  })

  it('sets unauthenticated on non-ok response and signs out', async () => {
    setupSupabaseMocks(mockSession)
    mockFetch.mockResolvedValue({ ok: false, status: 500 })

    render(<AuthProvider><StatusReader /></AuthProvider>)

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'),
    )
    expect(supabase.auth.signOut).toHaveBeenCalled()
  })

  it('sets unauthenticated when fetch throws a network error', async () => {
    setupSupabaseMocks(mockSession)
    mockFetch.mockRejectedValue(new Error('network error'))

    render(<AuthProvider><StatusReader /></AuthProvider>)

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'),
    )
  })

  it('signInWithGoogle calls supabase OAuth', async () => {
    setupSupabaseMocks(null)

    render(<AuthProvider><StatusReader /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))

    await userEvent.click(screen.getByText('sign-in'))

    expect(supabase.auth.signInWithOAuth).toHaveBeenCalledWith(
      expect.objectContaining({ provider: 'google' }),
    )
  })

  it('signOut calls supabase.auth.signOut', async () => {
    setupSupabaseMocks(null)

    render(<AuthProvider><StatusReader /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))

    await userEvent.click(screen.getByText('sign-out'))

    expect(supabase.auth.signOut).toHaveBeenCalled()
  })

  it('reacts to an onAuthStateChange event', async () => {
    // Capture the callback registered with onAuthStateChange
    let authChangeCb: ((event: string, session: typeof mockSession | null) => void) | null = null
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null }, error: null,
    })
    vi.mocked(supabase.auth.onAuthStateChange).mockImplementation((cb) => {
      authChangeCb = cb as typeof authChangeCb
      return { data: { subscription: { unsubscribe: vi.fn() } } } as never
    })
    mockFetch.mockResolvedValue({ ok: true, status: 200 })
    vi.mocked(supabase.auth.signOut).mockResolvedValue({ error: null })

    render(<AuthProvider><StatusReader /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'))

    // Simulate an external sign-in event
    const { act } = await import('@testing-library/react')
    await act(async () => { authChangeCb?.('SIGNED_IN', mockSession) })

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('authenticated'),
    )
  })
})

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    function BadConsumer() {
      useAuth()
      return null
    }

    expect(() => render(<BadConsumer />)).toThrow('useAuth must be used inside AuthProvider')
    spy.mockRestore()
  })
})
