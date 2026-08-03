import { useState, useEffect } from 'react'
import { Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { currentMonthValue, formatMonthYear } from '@/lib/months'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

type Bill = {
  id: string
  name: string
  due_day: number
  drive_folder_id: string
  start_date: string | null
}

type Props = {
  open: boolean
  onClose: () => void
  onRefresh: () => void
}

// start_month defaults to the current month: a new bill is only charged from
// the month it was registered, so earlier months are never flagged as overdue.
const emptyForm = () => ({
  name: '',
  due_day: '',
  drive_folder_id: '',
  start_month: currentMonthValue(),
})

export function ManageBillsModal({ open, onClose, onRefresh }: Props) {
  const [bills, setBills] = useState<Bill[]>([])
  const [form, setForm] = useState(emptyForm)
  const [submitting, setSubmitting] = useState(false)

  async function fetchBills() {
    const res = await api.get('/api/bills')
    setBills(await res.json())
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name || !form.due_day || !form.drive_folder_id || !form.start_month) return
    setSubmitting(true)
    const { start_month, ...rest } = form
    await api.post('/api/bills', {
      ...rest,
      due_day: Number(form.due_day),
      start_date: `${start_month}-01`,
    })
    setForm(emptyForm())
    await fetchBills()
    onRefresh()
    setSubmitting(false)
  }

  async function handleDelete(id: string) {
    await api.delete(`/api/bills/${id}`)
    await fetchBills()
    onRefresh()
  }

  useEffect(() => {
    if (open) fetchBills()
  }, [open])

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Gerenciar Contas</DialogTitle>
        </DialogHeader>

        {/* Bill list */}
        <div className="flex flex-col gap-1">
          {bills.length === 0 && (
            <p className="py-2 text-xs text-muted-foreground">Nenhuma conta cadastrada.</p>
          )}
          {bills.map((bill) => (
            <div
              key={bill.id}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-secondary"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground">{bill.name}</p>
                <p className="text-xs text-muted-foreground">
                  Dia {bill.due_day}
                  {bill.start_date && ` · desde ${formatMonthYear(bill.start_date)}`}
                  {' · '}
                  <span className="font-mono">{bill.drive_folder_id}</span>
                </p>
              </div>
              <button
                onClick={() => handleDelete(bill.id)}
                aria-label={`Excluir ${bill.name}`}
                className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="size-4" strokeWidth={1.5} />
              </button>
            </div>
          ))}
        </div>

        {/* Divider */}
        <div className="border-t border-border" />

        {/* Add form */}
        <form onSubmit={handleAdd} className="flex flex-col gap-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Nova conta</p>
          <div className="flex flex-col gap-2">
            <div className="grid grid-cols-2 gap-2">
              <Input
                placeholder="Nome da conta"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              <Input
                type="number"
                placeholder="Dia de vencimento"
                min={1}
                max={31}
                value={form.due_day}
                onChange={(e) => setForm({ ...form, due_day: e.target.value })}
              />
            </div>
            <Input
              placeholder="ID da pasta no Google Drive"
              value={form.drive_folder_id}
              onChange={(e) => setForm({ ...form, drive_folder_id: e.target.value })}
            />
            <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground">
              Início da cobrança
              <Input
                type="month"
                value={form.start_month}
                onChange={(e) => setForm({ ...form, start_month: e.target.value })}
              />
            </label>
            <p className="text-xs text-muted-foreground">
              Meses anteriores a essa data não entram nos avisos de comprovante
              em falta.
            </p>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-primary py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Adicionar
          </button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
