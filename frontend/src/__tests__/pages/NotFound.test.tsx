import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { NotFound } from '@/pages/NotFound'

describe('NotFound', () => {
  it('renders the 404 message', () => {
    render(<MemoryRouter><NotFound /></MemoryRouter>)
    expect(screen.getByText('404')).toBeInTheDocument()
    expect(screen.getByText('Página não encontrada')).toBeInTheDocument()
  })

  it('has a link back to home', () => {
    render(<MemoryRouter><NotFound /></MemoryRouter>)
    const link = screen.getByRole('link', { name: /voltar ao início/i })
    expect(link).toHaveAttribute('href', '/')
  })
})
