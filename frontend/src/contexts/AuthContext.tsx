import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'unauthorized'; email: string }
  | { status: 'authenticated'; user: User; session: Session }

const AuthContext = createContext<{
  auth: AuthState
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
} | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ status: 'loading' })

  const resolveAuth = useCallback(async (session: Session | null) => {
    if (!session) {
      setAuth({ status: 'unauthenticated' })
      return
    }

    const res = await fetch(`${API_BASE}/api/auth/verify`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    })

    if (res.status === 403) {
      await supabase.auth.signOut()
      setAuth({ status: 'unauthorized', email: session.user.email ?? '' })
      return
    }

    if (!res.ok) {
      await supabase.auth.signOut()
      setAuth({ status: 'unauthenticated' })
      return
    }

    setAuth({ status: 'authenticated', user: session.user, session })
  }, [])

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      resolveAuth(session)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      resolveAuth(session)
    })

    return () => subscription.unsubscribe()
  }, [resolveAuth])

  async function signInWithGoogle() {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  }

  async function signOut() {
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider value={{ auth, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
