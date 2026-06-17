import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronLeft, Settings2, Zap, Droplets, Wifi, Building2,
  Flame, ShoppingCart, Receipt, CheckCircle2, Circle, Upload, AlertTriangle,
  type LucideIcon,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ManageBillsModal } from '@/components/ManageBillsModal'
import { UploadReceiptModal } from '@/components/UploadReceiptModal'
import { api } from '@/lib/api'

type Bill = {
  id: string
  name: string
  due_day: number
  drive_folder_id: string
  paid: boolean
}

type MissingPayment = {
  name: string
  month: number
  month_name: string
}

const MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export function iconForBill(name: string): LucideIcon {
  const n = name.toLowerCase()
  if (n.includes('energia') || n.includes('luz')) return Zap
  if (n.includes('água') || n.includes('agua')) return Droplets
  if (n.includes('internet') || n.includes('wifi')) return Wifi
  if (n.includes('aluguel') || n.includes('condomínio') || n.includes('condominio')) return Building2
  if (n.includes('gás') || n.includes('gas')) return Flame
  if (n.includes('mercado') || n.includes('compra')) return ShoppingCart
  return Receipt
}

export function Bills() {
  const [bills, setBills] = useState<Bill[]>([])
  const [missing, setMissing] = useState<MissingPayment[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [uploadBill, setUploadBill] = useState<Bill | null>(null)

  const currentMonth = new Date().getMonth()

  async function fetchStatus() {
    setLoading(true)
    try {
      const res = await api.get('/api/bills/status')
      setBills(await res.json())
    } finally {
      setLoading(false)
    }
  }

  async function fetchMissing() {
    const res = await api.get('/api/bills/missing')
    if (res.ok) setMissing(await res.json())
  }

  function refresh() {
    fetchStatus()
    fetchMissing()
  }

  useEffect(() => {
    fetchStatus()
    fetchMissing()
  }, [])

  const paid = bills.filter((b) => b.paid).length

  // Group earlier-month gaps by bill so each appears once ("Água · Abril, Maio").
  const missingByBill = missing.reduce<{ name: string; months: string[] }[]>((acc, m) => {
    const entry = acc.find((e) => e.name === m.name)
    if (entry) entry.months.push(m.month_name)
    else acc.push({ name: m.name, months: [m.month_name] })
    return acc
  }, [])

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
              <p className="text-xs text-muted-foreground">
                {loading ? 'Verificando...' : `${paid} de ${bills.length} pagas`}
              </p>
            </div>
          </div>

          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <Settings2 className="size-4" strokeWidth={1.5} />
            Gerenciar
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex flex-col gap-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 rounded-lg bg-card animate-pulse" />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && bills.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <p className="text-sm text-muted-foreground">Nenhuma conta cadastrada.</p>
            <button
              onClick={() => setModalOpen(true)}
              className="text-sm text-foreground underline underline-offset-4"
            >
              Adicionar conta
            </button>
          </div>
        )}

        {/* Bill list */}
        {!loading && bills.length > 0 && (
          <div className="flex flex-col gap-2">
            {bills.map((bill) => {
              const Icon = iconForBill(bill.name)
              return (
                <div
                  key={bill.id}
                  className="flex w-full items-center gap-4 rounded-lg border border-border bg-card px-4 py-3.5"
                >
                  <Icon className="size-5 shrink-0 text-muted-foreground" strokeWidth={1.5} />

                  <span className="flex-1 text-sm font-medium text-foreground">{bill.name}</span>

                  <span className="text-xs text-muted-foreground">
                    Dia {bill.due_day} {MONTH_NAMES[currentMonth]}
                  </span>

                  {bill.paid ? (
                    <Badge variant="secondary" className="flex items-center gap-1 text-xs font-normal text-emerald-400">
                      <CheckCircle2 className="size-3.5" strokeWidth={1.5} />
                      Pago
                    </Badge>
                  ) : (
                    <>
                      <Badge variant="secondary" className="flex items-center gap-1 text-xs font-normal text-muted-foreground">
                        <Circle className="size-3.5" strokeWidth={1.5} />
                        Pendente
                      </Badge>
                      <button
                        onClick={() => setUploadBill(bill)}
                        aria-label={`Enviar comprovante de ${bill.name}`}
                        className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                      >
                        <Upload className="size-4" strokeWidth={1.5} />
                      </button>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Overdue from earlier months */}
        {!loading && missingByBill.length > 0 && (
          <div className="mt-10 rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3.5">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="size-4 shrink-0 text-amber-400" strokeWidth={1.5} />
              <span className="text-sm font-medium text-foreground">
                Contas de meses anteriores em aberto
              </span>
            </div>
            <ul className="mt-3 flex flex-col gap-2">
              {missingByBill.map(({ name, months }) => {
                const Icon = iconForBill(name)
                return (
                  <li key={name} className="flex items-center gap-2.5 text-xs">
                    <Icon className="size-3.5 shrink-0 text-muted-foreground" strokeWidth={1.5} />
                    <span className="font-medium text-foreground">{name}</span>
                    <span className="text-muted-foreground">{months.join(', ')}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

      </div>

      <ManageBillsModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onRefresh={refresh}
      />

      {uploadBill && (
        <UploadReceiptModal
          bill={uploadBill}
          onClose={() => setUploadBill(null)}
          onSuccess={() => {
            setUploadBill(null)
            refresh()
          }}
        />
      )}
    </div>
  )
}
