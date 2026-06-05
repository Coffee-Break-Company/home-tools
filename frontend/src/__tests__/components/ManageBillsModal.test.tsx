import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}))

// Render the dialog as a plain div when open, null when closed.
vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}))

import { ManageBillsModal } from '@/components/ManageBillsModal'
import { api } from '@/lib/api'

const mockBills = [
  { id: '1', name: 'Internet', due_day: 10, drive_folder_id: 'folder-1' },
  { id: '2', name: 'Energia', due_day: 15, drive_folder_id: 'folder-2' },
]

function makeJsonResponse(data: unknown) {
  return { json: () => Promise.resolve(data) } as Response
}

describe('ManageBillsModal', () => {
  const onClose = vi.fn()
  const onRefresh = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.get).mockResolvedValue(makeJsonResponse(mockBills))
    vi.mocked(api.post).mockResolvedValue(makeJsonResponse({}))
    vi.mocked(api.delete).mockResolvedValue({ ok: true } as Response)
  })

  it('fetches bills when modal is opened', async () => {
    render(<ManageBillsModal open onClose={onClose} onRefresh={onRefresh} />)

    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/api/bills'))
  })

  it('does not fetch when modal is closed', () => {
    render(<ManageBillsModal open={false} onClose={onClose} onRefresh={onRefresh} />)
    expect(api.get).not.toHaveBeenCalled()
  })

  it('shows empty-state message when there are no bills', async () => {
    vi.mocked(api.get).mockResolvedValue(makeJsonResponse([]))

    render(<ManageBillsModal open onClose={onClose} onRefresh={onRefresh} />)

    await waitFor(() =>
      expect(screen.getByText('Nenhuma conta cadastrada.')).toBeInTheDocument(),
    )
  })

  it('renders each bill with name and due day', async () => {
    render(<ManageBillsModal open onClose={onClose} onRefresh={onRefresh} />)

    await waitFor(() => {
      expect(screen.getByText('Internet')).toBeInTheDocument()
      expect(screen.getByText('Energia')).toBeInTheDocument()
    })
  })

  it('submits the form and calls onRefresh after adding a bill', async () => {
    const user = userEvent.setup()
    render(<ManageBillsModal open onClose={onClose} onRefresh={onRefresh} />)

    await waitFor(() => expect(api.get).toHaveBeenCalled())

    await user.type(screen.getByPlaceholderText('Nome da conta'), 'Água')
    await user.type(screen.getByPlaceholderText('Dia de vencimento'), '5')
    await user.type(screen.getByPlaceholderText('ID da pasta no Google Drive'), 'folder-xyz')
    await user.click(screen.getByRole('button', { name: 'Adicionar' }))

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith('/api/bills', {
        name: 'Água',
        due_day: 5,
        drive_folder_id: 'folder-xyz',
      }),
    )
    expect(onRefresh).toHaveBeenCalled()
  })

  it('does not submit when the form is incomplete', async () => {
    const user = userEvent.setup()
    render(<ManageBillsModal open onClose={onClose} onRefresh={onRefresh} />)

    await waitFor(() => expect(api.get).toHaveBeenCalled())

    await user.type(screen.getByPlaceholderText('Nome da conta'), 'Água')
    await user.click(screen.getByRole('button', { name: 'Adicionar' }))

    expect(api.post).not.toHaveBeenCalled()
  })

  it('deletes a bill when the trash button is clicked', async () => {
    const user = userEvent.setup()
    render(<ManageBillsModal open onClose={onClose} onRefresh={onRefresh} />)

    await waitFor(() => expect(screen.getByText('Internet')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Excluir Internet' }))

    await waitFor(() =>
      expect(api.delete).toHaveBeenCalledWith('/api/bills/1'),
    )
    expect(onRefresh).toHaveBeenCalled()
  })
})
