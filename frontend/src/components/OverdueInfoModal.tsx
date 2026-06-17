import { FolderOpen } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

type Props = {
  items: { name: string; months: string[] }[]
  onClose: () => void
}

export function OverdueInfoModal({ items, onClose }: Props) {
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Pagamentos de meses anteriores</DialogTitle>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          Para registrar esses pagamentos, adicione os comprovantes manualmente
          nas respectivas pastas das contas, diretamente no Google Drive.
        </p>

        <ul className="flex flex-col gap-2">
          {items.map(({ name, months }) => (
            <li key={name} className="flex items-center gap-2.5 text-xs">
              <FolderOpen className="size-3.5 shrink-0 text-muted-foreground" strokeWidth={1.5} />
              <span className="font-medium text-foreground">{name}</span>
              <span className="text-muted-foreground">{months.join(', ')}</span>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  )
}
