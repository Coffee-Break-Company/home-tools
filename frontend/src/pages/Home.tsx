import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Home as HomeIcon, Wallet, type LucideIcon } from 'lucide-react'

type Module = {
  id: string
  title: string
  description: string
  path: string
  icon: LucideIcon
  status: string
  available: boolean
}

const modules: Module[] = [
  {
    id: 'bills',
    title: 'Contas de Casa',
    description: 'Acompanhe e gerencie as despesas domésticas',
    path: '/contas',
    icon: HomeIcon,
    status: 'Em breve',
    available: true,
  },
  {
    id: 'finance',
    title: 'Finanças Pessoais',
    description: 'Controle sua renda, gastos e metas financeiras',
    path: '/finance',
    icon: Wallet,
    status: 'Em breve',
    available: false,
  },
]

export function Home() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6">
        <header className="mb-14 text-center">
          <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
            Home Tools
          </h1>
          <p className="mt-3 text-sm text-muted-foreground">
            Seus utilitários domésticos em um só lugar
          </p>
        </header>

        <div className="grid gap-3 sm:grid-cols-2">
          {modules.map((mod) => {
            const content = (
              <Card
                key={mod.id}
                className={`border-border/50 bg-card transition-all duration-200 ${
                  mod.available
                    ? 'cursor-pointer hover:border-border hover:bg-secondary'
                    : 'opacity-80'
                }`}
              >
                <CardHeader className="gap-4 p-5">
                  <div className="flex items-start justify-between">
                    <mod.icon className="size-6 text-foreground" strokeWidth={1.5} />
                    {!mod.available && (
                      <Badge variant="secondary" className="text-xs font-normal">
                        {mod.status}
                      </Badge>
                    )}
                  </div>
                  <div>
                    <CardTitle className="text-base font-medium">{mod.title}</CardTitle>
                    <CardDescription className="mt-1 text-xs leading-relaxed">
                      {mod.description}
                    </CardDescription>
                  </div>
                </CardHeader>
              </Card>
            )

            return mod.available ? (
              <Link key={mod.id} to={mod.path} className="no-underline">
                {content}
              </Link>
            ) : (
              <div key={mod.id}>{content}</div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
