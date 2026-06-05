import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import type { ReactNode } from 'react'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { auth } = useAuth()

  if (auth.status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="size-5 animate-spin rounded-full border-2 border-muted-foreground border-t-foreground" />
      </div>
    )
  }

  if (auth.status === 'unauthenticated' || auth.status === 'unauthorized') {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
