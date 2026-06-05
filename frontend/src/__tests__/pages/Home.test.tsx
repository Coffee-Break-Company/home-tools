import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Home } from '@/pages/Home'

function renderHome() {
  render(<MemoryRouter><Home /></MemoryRouter>)
}

describe('Home', () => {
  it('renders the page title', () => {
    renderHome()
    expect(screen.getByRole('heading', { name: 'Home Tools' })).toBeInTheDocument()
  })

  it('renders all module cards', () => {
    renderHome()
    expect(screen.getByText('Contas de Casa')).toBeInTheDocument()
    expect(screen.getByText('Finanças Pessoais')).toBeInTheDocument()
  })

  it('available module is wrapped in a link to its path', () => {
    renderHome()
    const link = screen.getByRole('link', { name: /contas de casa/i })
    expect(link).toHaveAttribute('href', '/contas')
  })

  it('unavailable module shows the "Em breve" badge', () => {
    renderHome()
    expect(screen.getByText('Em breve')).toBeInTheDocument()
  })

  it('unavailable module is not a link', () => {
    renderHome()
    const hrefs = screen.getAllByRole('link').map((l) => l.getAttribute('href'))
    expect(hrefs).not.toContain('/finance')
  })
})
