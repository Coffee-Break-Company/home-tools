import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, Settings2, Zap, Droplets, Wifi, Building2, Flame, ShoppingCart, CheckCircle2, Circle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { type LucideIcon } from 'lucide-react'

type Bill = {
  id: number
  name: string
  icon: LucideIcon
  dueDay: number
  dueMonth: number
  paid: boolean
}

const MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

const initialBills: Bill[] = [
  { id: 1, name: 'Aluguel',      icon: Building2,    dueDay: 5,  dueMonth: 6, paid: true  },
  { id: 2, name: 'Condomínio',   icon: Building2,    dueDay: 10, dueMonth: 6, paid: true  },
  { id: 3, name: 'Energia',      icon: Zap,          dueDay: 12, dueMonth: 6, paid: false },
  { id: 4, name: 'Água',         icon: Droplets,     dueDay: 15, dueMonth: 6, paid: false },
  { id: 5, name: 'Internet',     icon: Wifi,         dueDay: 18, dueMonth: 6, paid: false },
  { id: 6, name: 'Gás',          icon: Flame,        dueDay: 20, dueMonth: 6, paid: false },
  { id: 7, name: 'Supermercado', icon: ShoppingCart, dueDay: 25, dueMonth: 6, paid: false },
]

export function Bills() {
  const [bills, setBills] = useState<Bill[]>(initialBills)

  function togglePaid(id: number) {
    setBills((prev) =>
      prev.map((b) => (b.id === id ? { ...b, paid: !b.paid } : b))
    )
  }

  const paid = bills.filter((b) => b.paid).length

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">

        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              <ChevronLeft className="size-5" strokeWidth={1.5} />
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-foreground">Contas de Casa</h1>
              <p className="text-xs text-muted-foreground">{paid} de {bills.length} pagas</p>
            </div>
          </div>

          <button className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground">
            <Settings2 className="size-4" strokeWidth={1.5} />
            Gerenciar
          </button>
        </div>

        {/* Bill list */}
        <div className="flex flex-col gap-2">
          {bills.map((bill) => (
            <button
              key={bill.id}
              onClick={() => togglePaid(bill.id)}
              className="flex w-full items-center gap-4 rounded-lg border border-border bg-card px-4 py-3.5 text-left transition-colors hover:bg-secondary"
            >
              <bill.icon
                className="size-5 shrink-0 text-muted-foreground"
                strokeWidth={1.5}
              />

              <span className="flex-1 text-sm font-medium text-foreground">{bill.name}</span>

              <span className="text-xs text-muted-foreground">
                Dia {bill.dueDay} {MONTH_NAMES[bill.dueMonth - 1]}
              </span>

              {bill.paid ? (
                <Badge variant="secondary" className="flex items-center gap-1 text-xs font-normal text-emerald-400">
                  <CheckCircle2 className="size-3.5" strokeWidth={1.5} />
                  Pago
                </Badge>
              ) : (
                <Badge variant="secondary" className="flex items-center gap-1 text-xs font-normal text-muted-foreground">
                  <Circle className="size-3.5" strokeWidth={1.5} />
                  Pendente
                </Badge>
              )}
            </button>
          ))}
        </div>

      </div>
    </div>
  )
}
