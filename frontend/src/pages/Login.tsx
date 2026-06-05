import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Home } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  )
}

export function Login() {
  const { auth, signInWithGoogle } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (auth.status === 'authenticated') navigate('/', { replace: true })
  }, [auth.status, navigate])

  const isUnauthorized = auth.status === 'unauthorized'

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      {/* Logo */}
      <div className="mb-6 flex items-center gap-2.5">
        <div className="flex size-8 items-center justify-center rounded-lg bg-foreground">
          <Home className="size-4 text-background" strokeWidth={1.75} />
        </div>
        <span className="text-sm font-semibold text-foreground">Home Tools</span>
      </div>

      {/* Card */}
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-lg font-semibold">Bem-vindo de volta</CardTitle>
          <CardDescription>Entre com sua conta Google</CardDescription>
        </CardHeader>

        <CardContent className="flex flex-col gap-3">
          {isUnauthorized && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-center text-xs text-destructive">
              Acesso negado para{' '}
              <span className="font-medium">{(auth as { email: string }).email}</span>.
              <br />
              Este email não está na lista de usuários autorizados.
            </p>
          )}

          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={signInWithGoogle}
          >
            <GoogleIcon />
            Entrar com Google
          </Button>
        </CardContent>

        <CardFooter className="justify-center border-t bg-muted/30">
          <p className="text-center text-xs text-muted-foreground">
            Ao continuar, você concorda com nossos{' '}
            <span className="underline underline-offset-2">Termos de Serviço</span>
            {' '}e{' '}
            <span className="underline underline-offset-2">Política de Privacidade</span>.
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
