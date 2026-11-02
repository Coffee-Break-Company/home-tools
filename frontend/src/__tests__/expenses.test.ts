import { describe, it, expect } from 'vitest'
import { CreditCard, Croissant, Fuel, Pill, ShoppingCart, UtensilsCrossed } from 'lucide-react'
import {
  currentMonth, dayKey, formatCurrency, formatDayLabel, groupByDay, iconForMerchant,
  shiftMonth, summarize, DEFAULT_CATEGORY, type Expense,
} from '@/lib/expenses'

function expense(partial: Partial<Expense>): Expense {
  return {
    id: crypto.randomUUID(), amount: 10, merchant: 'Loja', card: 'Nubank',
    occurred_at: '2026-11-01T12:00:00Z', source: 'apple_pay', ...partial,
  }
}

describe('dayKey', () => {
  it('uses Brasília time, not UTC', () => {
    // 01:30 UTC on Nov 2 is still Nov 1 in Brasília (UTC-3).
    expect(dayKey('2026-11-02T01:30:00Z')).toBe('2026-11-01')
  })
})

describe('formatDayLabel', () => {
  const now = new Date('2026-11-02T15:00:00Z')
  it('labels today and yesterday', () => {
    expect(formatDayLabel('2026-11-02', now)).toBe('Hoje')
    expect(formatDayLabel('2026-11-01', now)).toBe('Ontem')
  })
  it('labels older days with weekday and date', () => {
    expect(formatDayLabel('2026-10-28', now)).toMatch(/^Qua.*28.*out/)
  })
})

describe('formatCurrency', () => {
  it('formats as BRL', () => {
    expect(formatCurrency(1234.5).replace(/\s/g, ' ')).toBe('R$ 1.234,50')
  })
})

describe('iconForMerchant', () => {
  it.each([
    ['Padaria Pão Quente', Croissant],
    ['Supermercado Extra', ShoppingCart],
    ['Posto Shell', Fuel],
    ['Farmácia São João', Pill],
    ['iFood', UtensilsCrossed],
    ['XPTO Serviços', CreditCard],
    [null, CreditCard],
  ])('"%s" → correct icon', (merchant, icon) => {
    expect(iconForMerchant(merchant)).toBe(icon)
  })
})

describe('groupByDay', () => {
  it('groups consecutive expenses of the same Brasília day and sums them', () => {
    const groups = groupByDay([
      expense({ amount: 5, occurred_at: '2026-11-02T01:00:00Z' }), // Nov 1, 22:00 BRT
      expense({ amount: 7, occurred_at: '2026-11-01T12:00:00Z' }),
      expense({ amount: null, occurred_at: '2026-10-31T12:00:00Z' }),
    ])
    expect(groups.map((g) => [g.key, g.total, g.items.length])).toEqual([
      ['2026-11-01', 12, 2],
      ['2026-10-31', 0, 1],
    ])
  })
})

describe('summarize', () => {
  const expenses = [
    expense({ amount: 100, merchant: 'Mercado', card: 'Itaú', occurred_at: '2026-11-03T12:00:00Z' }),
    expense({ amount: 20, merchant: 'Padaria', card: 'Nubank', occurred_at: '2026-11-03T13:00:00Z' }),
    expense({ amount: 30, merchant: 'Padaria', card: 'Nubank', occurred_at: '2026-11-10T13:00:00Z' }),
    expense({ amount: null, merchant: 'Farmácia', card: null, occurred_at: '2026-11-10T14:00:00Z' }),
  ]
  const s = summarize(expenses, '2026-11')

  it('totals and averages only priced expenses', () => {
    expect(s.total).toBe(150)
    expect(s.count).toBe(4)
    expect(s.missingAmount).toBe(1)
    expect(s.average).toBe(50)
    expect(s.largest?.merchant).toBe('Mercado')
  })

  it('puts everything in the single default category', () => {
    expect(s.byCategory).toEqual([{ name: DEFAULT_CATEGORY, total: 150, count: 4 }])
  })

  it('ranks cards and merchants by total', () => {
    expect(s.byCard.map((c) => c.name)).toEqual(['Itaú', 'Nubank', 'Sem cartão'])
    expect(s.topMerchants[0]).toEqual({ name: 'Mercado', total: 100, count: 1 })
    expect(s.topMerchants[1]).toEqual({ name: 'Padaria', total: 50, count: 2 })
  })

  it('builds a per-day series the length of the month', () => {
    expect(s.daily).toHaveLength(30)
    expect(s.daily[2]).toBe(120)
    expect(s.daily[9]).toBe(30)
  })
})

describe('months', () => {
  it('shifts across year boundaries', () => {
    expect(shiftMonth('2026-01', -1)).toBe('2025-12')
    expect(shiftMonth('2026-12', 1)).toBe('2027-01')
  })
  it('current month follows Brasília time', () => {
    expect(currentMonth(new Date('2026-12-01T02:00:00Z'))).toBe('2026-11')
  })
})
