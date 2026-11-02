import {
  Car, Croissant, CreditCard, Fuel, Pill, ShoppingBag, ShoppingCart, SquareParking,
  UtensilsCrossed, type LucideIcon,
} from 'lucide-react'

export type Expense = {
  id: string
  amount: number | null
  merchant: string | null
  card: string | null
  occurred_at: string
  source: string
}

// Everything is shown in Brasília time, whatever the device's timezone.
const TZ = 'America/Sao_Paulo'

// Until expenses are classified (e.g. by an LLM), they all share one category.
export const DEFAULT_CATEGORY = 'Sem categoria'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const dayKeyFormat = new Intl.DateTimeFormat('en-CA', {
  timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
})
const timeFormat = new Intl.DateTimeFormat('pt-BR', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })
const dayLabelFormat = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short',
})

export function formatCurrency(value: number): string {
  return currency.format(value)
}

/** 'YYYY-MM-DD' of the instant, in Brasília time. */
export function dayKey(iso: string | Date): string {
  return dayKeyFormat.format(typeof iso === 'string' ? new Date(iso) : iso)
}

export function formatTime(iso: string): string {
  return timeFormat.format(new Date(iso))
}

/** 'Hoje', 'Ontem' or e.g. 'sáb., 1 de nov.' for a 'YYYY-MM-DD' key. */
export function formatDayLabel(key: string, now: Date = new Date()): string {
  const today = dayKey(now)
  if (key === today) return 'Hoje'
  const yesterday = dayKey(new Date(now.getTime() - 24 * 60 * 60 * 1000))
  if (key === yesterday) return 'Ontem'
  // The key is already a Brasília date; format it as a plain UTC date.
  // Intl abbreviates with dots ("sáb., 1 de nov."); drop them for a cleaner label.
  const label = dayLabelFormat.format(new Date(`${key}T12:00:00Z`)).replace(/\./g, '')
  return label.charAt(0).toUpperCase() + label.slice(1)
}

export function iconForMerchant(merchant: string | null): LucideIcon {
  const n = (merchant ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  if (/padaria|panificadora|cafe/.test(n)) return Croissant
  if (/mercado|atacad|hortifruti|carrefour|assai/.test(n)) return ShoppingCart
  if (/posto|shell|ipiranga|petrobras|combust/.test(n)) return Fuel
  if (/farmacia|drogaria|droga ?raia|pacheco/.test(n)) return Pill
  if (/estacionamento|parking|estapar/.test(n)) return SquareParking
  if (/ifood|restaurante|lanchonete|pizzaria|burger|bar /.test(n)) return UtensilsCrossed
  if (/uber|99 ?app|taxi|\b99\b/.test(n)) return Car
  if (/loja|shopping|magazine|amazon|mercado ?livre/.test(n)) return ShoppingBag
  return CreditCard
}

export type DayGroup = { key: string; total: number; items: Expense[] }

/** Groups expenses (already newest first) by Brasília day, keeping the order. */
export function groupByDay(expenses: Expense[]): DayGroup[] {
  const groups: DayGroup[] = []
  for (const e of expenses) {
    const key = dayKey(e.occurred_at)
    let group = groups[groups.length - 1]
    if (!group || group.key !== key) {
      group = { key, total: 0, items: [] }
      groups.push(group)
    }
    group.items.push(e)
    group.total += e.amount ?? 0
  }
  return groups
}

export type Share = { name: string; total: number; count: number }

function sumBy(expenses: Expense[], keyOf: (e: Expense) => string): Share[] {
  const map = new Map<string, Share>()
  for (const e of expenses) {
    const name = keyOf(e)
    const share = map.get(name) ?? { name, total: 0, count: 0 }
    share.total += e.amount ?? 0
    share.count += 1
    map.set(name, share)
  }
  return [...map.values()].sort((a, b) => b.total - a.total || b.count - a.count)
}

export type Summary = {
  total: number
  count: number
  average: number
  largest: Expense | null
  missingAmount: number
  byCategory: Share[]
  byCard: Share[]
  topMerchants: Share[]
  /** Total per day of the month, index 0 = day 1. */
  daily: number[]
}

/** `month` is 'YYYY-MM'; it sizes the daily series. */
export function summarize(expenses: Expense[], month: string): Summary {
  const priced = expenses.filter((e) => e.amount !== null)
  const total = priced.reduce((s, e) => s + (e.amount ?? 0), 0)
  const largest = priced.reduce<Expense | null>(
    (max, e) => (max === null || (e.amount ?? 0) > (max.amount ?? 0) ? e : max), null,
  )

  const [year, mon] = month.split('-').map(Number)
  const daysInMonth = new Date(Date.UTC(year, mon, 0)).getUTCDate()
  const daily = Array<number>(daysInMonth).fill(0)
  for (const e of priced) {
    const day = Number(dayKey(e.occurred_at).slice(8, 10))
    daily[day - 1] += e.amount ?? 0
  }

  return {
    total,
    count: expenses.length,
    average: priced.length ? total / priced.length : 0,
    largest,
    missingAmount: expenses.length - priced.length,
    byCategory: sumBy(expenses, () => DEFAULT_CATEGORY),
    byCard: sumBy(expenses, (e) => e.card ?? 'Sem cartão'),
    topMerchants: sumBy(expenses, (e) => e.merchant ?? 'Sem estabelecimento').slice(0, 5),
    daily,
  }
}

/** 'YYYY-MM' shifted by `delta` months. */
export function shiftMonth(month: string, delta: number): string {
  const [year, mon] = month.split('-').map(Number)
  const d = new Date(Date.UTC(year, mon - 1 + delta, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

/** The current month in Brasília time, as 'YYYY-MM'. */
export function currentMonth(now: Date = new Date()): string {
  return dayKey(now).slice(0, 7)
}
