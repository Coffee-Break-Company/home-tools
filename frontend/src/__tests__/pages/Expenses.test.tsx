import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn() },
}))

import { Expenses } from '@/pages/Expenses'
import { api } from '@/lib/api'
import { currentMonth } from '@/lib/expenses'

const month = currentMonth()
const mockExpenses = [
  { id: '1', amount: 42.9, merchant: 'Padaria Pão Quente', card: 'Nubank',
    occurred_at: `${month}-01T11:15:00Z`, source: 'apple_pay' },
  { id: '2', amount: null, merchant: 'Farmácia São João', card: 'Inter',
    occurred_at: `${month}-01T10:00:00Z`, source: 'apple_pay' },
]

function respond(data: unknown, ok = true) {
  return { ok, json: () => Promise.resolve(data) } as Response
}

function renderPage() {
  render(<MemoryRouter><Expenses /></MemoryRouter>)
}

// Currency strings use a non-breaking space after "R$".
const brl = (text: string) => (content: string) => content.replace(/\s/g, ' ') === text

describe('Expenses page', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches the current month of real expenses', async () => {
    vi.mocked(api.get).mockResolvedValue(respond(mockExpenses))
    renderPage()
    await screen.findByText('Padaria Pão Quente')
    expect(api.get).toHaveBeenCalledWith(`/api/expenses?month=${month}&test=false`)
  })

  it('shows the month total and the list with a "Sem valor" badge', async () => {
    vi.mocked(api.get).mockResolvedValue(respond(mockExpenses))
    renderPage()
    await screen.findByText('Farmácia São João')
    expect(screen.getAllByText(brl('R$ 42,90')).length).toBeGreaterThan(0)
    expect(screen.getByText('Sem valor')).toBeInTheDocument()
    expect(screen.getByText('2 gastos · 1 sem valor')).toBeInTheDocument()
  })

  it('switches to the summary tab with tiles', async () => {
    vi.mocked(api.get).mockResolvedValue(respond(mockExpenses))
    renderPage()
    await screen.findByText('Padaria Pão Quente')
    await userEvent.click(screen.getByRole('tab', { name: /resumo/i }))
    expect(await screen.findByText('Média por gasto')).toBeInTheDocument()
    expect(screen.getByText('Por categoria')).toBeInTheDocument()
    expect(screen.getByText('Sem categoria')).toBeInTheDocument()
  })

  it('test-data switch refetches only test rows', async () => {
    vi.mocked(api.get).mockResolvedValue(respond([]))
    renderPage()
    await screen.findByText(/Nenhum gasto/)
    await userEvent.click(screen.getByRole('switch', { name: 'Dados de teste' }))
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(`/api/expenses?month=${month}&test=true`),
    )
    expect(await screen.findByText('Nenhum dado de teste neste mês.')).toBeInTheDocument()
  })

  it('previous-month button loads the earlier month; next is disabled on the current one', async () => {
    vi.mocked(api.get).mockResolvedValue(respond([]))
    renderPage()
    await screen.findByText(/Nenhum gasto/)
    expect(screen.getByRole('button', { name: 'Próximo mês' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Mês anterior' }))
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2))
    expect(vi.mocked(api.get).mock.calls[1][0]).not.toContain(`month=${month}&`)
  })

  it('shows an error message when the request fails', async () => {
    vi.mocked(api.get).mockResolvedValue(respond({ detail: 'x' }, false))
    renderPage()
    expect(await screen.findByText('Não foi possível carregar os gastos.')).toBeInTheDocument()
  })
})
