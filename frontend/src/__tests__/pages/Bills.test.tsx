import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Zap, Droplets, Wifi, Building2, Flame, ShoppingCart, Receipt } from 'lucide-react'

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn() },
}))

vi.mock('@/components/ManageBillsModal', () => ({
  ManageBillsModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="manage-modal">Modal</div> : null,
}))

import { Bills, iconForBill } from '@/pages/Bills'
import { api } from '@/lib/api'

const mockBills = [
  { id: '1', name: 'Energia Elétrica', due_day: 10, drive_folder_id: 'f1', paid: true },
  { id: '2', name: 'Água', due_day: 5, drive_folder_id: 'f2', paid: false },
]

function makeJsonResponse(data: unknown) {
  return { json: () => Promise.resolve(data) } as Response
}

function renderBills() {
  render(<MemoryRouter><Bills /></MemoryRouter>)
}

describe('iconForBill', () => {
  it.each([
    ['Energia Elétrica', Zap],
    ['Luz da Rua', Zap],
    ['Água', Droplets],
    ['Agua', Droplets],
    ['Internet Fibra', Wifi],
    ['WiFi Casa', Wifi],
    ['Aluguel', Building2],
    ['Condomínio', Building2],
    ['Condominio', Building2],
    ['Gás', Flame],
    ['Gas Natural', Flame],
    ['Mercado Semanal', ShoppingCart],
    ['Compras do Mês', ShoppingCart],
    ['Plano de Saúde', Receipt],
  ])('"%s" → correct icon', (name, expected) => {
    expect(iconForBill(name)).toBe(expected)
  })
})

describe('Bills page', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows loading skeletons while fetching', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}))
    renderBills()
    expect(document.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('renders bills after loading', async () => {
    vi.mocked(api.get).mockResolvedValue(makeJsonResponse(mockBills))
    renderBills()
    await waitFor(() => expect(screen.getByText('Energia Elétrica')).toBeInTheDocument())
    expect(screen.getByText('Água')).toBeInTheDocument()
  })

  it('shows "Pago" and "Pendente" badges', async () => {
    vi.mocked(api.get).mockResolvedValue(makeJsonResponse(mockBills))
    renderBills()
    await waitFor(() => {
      expect(screen.getByText('Pago')).toBeInTheDocument()
      expect(screen.getByText('Pendente')).toBeInTheDocument()
    })
  })

  it('shows payment summary in the header', async () => {
    vi.mocked(api.get).mockResolvedValue(makeJsonResponse(mockBills))
    renderBills()
    await waitFor(() => expect(screen.getByText('1 de 2 pagas')).toBeInTheDocument())
  })

  it('shows empty state when there are no bills', async () => {
    vi.mocked(api.get).mockResolvedValue(makeJsonResponse([]))
    renderBills()
    await waitFor(() =>
      expect(screen.getByText('Nenhuma conta cadastrada.')).toBeInTheDocument(),
    )
  })

  it('opens the manage modal when "Gerenciar" is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue(makeJsonResponse(mockBills))
    renderBills()
    await waitFor(() => expect(screen.getByText('Energia Elétrica')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /gerenciar/i }))

    expect(screen.getByTestId('manage-modal')).toBeInTheDocument()
  })
})
