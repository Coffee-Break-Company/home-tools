import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-center">
      <p className="text-6xl font-bold text-muted-foreground">404</p>
      <p className="text-xl text-foreground">Página não encontrada</p>
      <Link
        to="/"
        className="inline-flex items-center rounded-md border border-input px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
      >
        Voltar ao início
      </Link>
    </div>
  )
}
