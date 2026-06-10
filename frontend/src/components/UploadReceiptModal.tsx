import { useRef, useState } from 'react'
import { Paperclip } from 'lucide-react'
import { api } from '@/lib/api'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

type Props = {
  bill: { id: string; name: string }
  onClose: () => void
  onSuccess: () => void
}

const MONTHS = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

export function UploadReceiptModal({ bill, onClose, onSuccess }: Props) {
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setSubmitting(true)
    setError(null)
    const data = new FormData()
    data.append('month', String(month))
    data.append('file', file)
    try {
      const res = await api.postForm(`/api/bills/${bill.id}/receipt`, data)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        setError(body?.detail ?? 'Falha ao enviar o comprovante. Tente novamente.')
        return
      }
      onSuccess()
    } catch {
      setError('Falha ao enviar o comprovante. Verifique sua conexão.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Enviar comprovante</DialogTitle>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          {bill.name} — o arquivo vai para a pasta da conta no Drive com o nome
          do mês escolhido, e a conta fica marcada como paga.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground">
            Mês do comprovante
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {MONTHS.map((name, i) => (
                <option key={name} value={i + 1}>{name}</option>
              ))}
            </select>
          </label>

          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex h-10 w-full items-center justify-center gap-2 rounded-md border border-dashed border-border px-3 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <Paperclip className="size-4" strokeWidth={1.5} />
            <span className="truncate">
              {file ? file.name : 'Escolher arquivo (PDF ou imagem)'}
            </span>
          </button>

          {error && <p className="text-xs text-destructive">{error}</p>}

          <button
            type="submit"
            disabled={!file || submitting}
            className="w-full rounded-lg bg-primary py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? 'Enviando...' : 'Enviar'}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
