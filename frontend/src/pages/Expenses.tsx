import { createElement, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, FlaskConical, LayoutGrid, List } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'
import {
  currentMonth, dayKey, formatCurrency, formatDayLabel, formatTime, groupByDay, iconForMerchant,
  shiftMonth, summarize, type Expense, type Share, type Summary,
} from '@/lib/expenses'
import { MONTH_NAMES_FULL } from '@/lib/months'
import { cn } from '@/lib/utils'

function monthLabel(month: string): string {
  const [year, mon] = month.split('-').map(Number)
  return `${MONTH_NAMES_FULL[mon - 1]} ${year}`
}

export function Expenses() {
  const thisMonth = currentMonth()
  const [month, setMonth] = useState(thisMonth)
  const [testData, setTestData] = useState(false)
  // The last response, tagged with the query it answers: while it doesn't match
  // the current query, a new one is in flight and the page shows as loading.
  const query = `/api/expenses?month=${month}&test=${testData}`
  const [result, setResult] = useState<{ query: string; expenses: Expense[]; error: boolean }>()

  useEffect(() => {
    let cancelled = false
    api.get(query)
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status))
        const expenses: Expense[] = await res.json()
        if (!cancelled) setResult({ query, expenses, error: false })
      })
      .catch(() => {
        if (!cancelled) setResult({ query, expenses: [], error: true })
      })
    return () => {
      cancelled = true
    }
  }, [query])

  const loading = result?.query !== query
  const expenses = loading ? [] : result.expenses
  const error = !loading && result.error
  const summary = summarize(expenses, month)
  const [, monthNumber] = month.split('-').map(Number)
  const monthName = MONTH_NAMES_FULL[monthNumber - 1]

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8">

        {/* Header */}
        <div className="mb-6 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              aria-label="Voltar"
              className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            >
              <ChevronLeft className="size-5" strokeWidth={1.5} />
            </Link>
            <h1 className="text-xl font-semibold text-foreground">Gastos</h1>
            {testData && (
              <Badge variant="secondary" className="gap-1 font-normal text-amber-400">
                <FlaskConical strokeWidth={1.5} />
                Teste
              </Badge>
            )}
          </div>

          {/* Not a <label>: wrapping the switch in one toggles it twice per click. */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span aria-hidden>Dados de teste</span>
            <Switch checked={testData} onCheckedChange={setTestData} aria-label="Dados de teste" />
          </div>
        </div>

        {/* Month + hero total */}
        <section className="mb-8">
          <div className="flex items-center justify-between">
            <p className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Total de {monthName}
            </p>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setMonth(shiftMonth(month, -1))}
                aria-label="Mês anterior"
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <ChevronLeft className="size-4" strokeWidth={1.5} />
              </button>
              <span className="min-w-28 text-center text-sm text-foreground">{monthLabel(month)}</span>
              <button
                type="button"
                onClick={() => setMonth(shiftMonth(month, 1))}
                disabled={month >= thisMonth}
                aria-label="Próximo mês"
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
              >
                <ChevronRight className="size-4" strokeWidth={1.5} />
              </button>
            </div>
          </div>

          {loading ? (
            <div className="mt-2 h-12 w-56 animate-pulse rounded-lg bg-card" />
          ) : (
            <p className="mt-1 text-5xl font-semibold tracking-tight text-foreground">
              {formatCurrency(summary.total)}
            </p>
          )}
          <p className="mt-2 text-sm text-muted-foreground">
            {loading ? 'Carregando...' : countLabel(summary)}
          </p>
        </section>

        {error && (
          <p className="mb-6 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            Não foi possível carregar os gastos.
          </p>
        )}

        <Tabs defaultValue="lista">
          <TabsList className="w-full group-data-horizontal/tabs:h-10 sm:w-fit">
            <TabsTrigger value="lista" className="px-4"><List strokeWidth={1.5} />Lista</TabsTrigger>
            <TabsTrigger value="resumo" className="px-4"><LayoutGrid strokeWidth={1.5} />Resumo</TabsTrigger>
          </TabsList>

          <TabsContent value="lista" className="pt-2">
            {loading ? <ListSkeleton /> : expenses.length === 0 ? (
              <EmptyState monthName={monthName} testData={testData} />
            ) : (
              <Timeline expenses={expenses} />
            )}
          </TabsContent>

          <TabsContent value="resumo" className="pt-2">
            {loading ? <ListSkeleton /> : expenses.length === 0 ? (
              <EmptyState monthName={monthName} testData={testData} />
            ) : (
              <SummaryView summary={summary} month={month} />
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

function countLabel(summary: Summary): string {
  const count = `${summary.count} ${summary.count === 1 ? 'gasto' : 'gastos'}`
  if (!summary.missingAmount) return count
  return `${count} · ${summary.missingAmount} sem valor`
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-14 animate-pulse rounded-lg bg-card" />
      ))}
    </div>
  )
}

function EmptyState({ monthName, testData }: { monthName: string; testData: boolean }) {
  return (
    <div className="flex flex-col items-center gap-1 py-16 text-center">
      <p className="text-sm text-foreground">Nenhum gasto em {monthName}.</p>
      <p className="text-xs text-muted-foreground">
        {testData
          ? 'Nenhum dado de teste neste mês.'
          : 'Os pagamentos com Apple Pay aparecem aqui automaticamente.'}
      </p>
    </div>
  )
}

/* ── Lista ──────────────────────────────────────────────────────────────── */

function Timeline({ expenses }: { expenses: Expense[] }) {
  const groups = groupByDay(expenses)
  return (
    <ol className="flex flex-col gap-6">
      {groups.map((group) => (
        <li key={group.key}>
          <div className="mb-1 flex items-baseline justify-between pl-1 pr-3">
            <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {formatDayLabel(group.key)}
            </h3>
            <span className="text-xs tabular-nums text-muted-foreground">
              {formatCurrency(group.total)}
            </span>
          </div>

          {/* The rail: a hairline the item nodes sit on. */}
          <ul className="relative ml-5 border-l border-border">
            {group.items.map((e) => <TimelineItem key={e.id} expense={e} />)}
          </ul>
        </li>
      ))}
    </ol>
  )
}

/** The icon matching a merchant; a fixed component so none is created per render. */
function MerchantIcon({ merchant, className }: { merchant: string | null; className?: string }) {
  return createElement(iconForMerchant(merchant), { className, strokeWidth: 1.5 })
}

function TimelineItem({ expense }: { expense: Expense }) {
  const details = [expense.card, formatTime(expense.occurred_at)].filter(Boolean).join(' · ')
  return (
    <li className="relative flex items-center gap-3 py-2 pl-7">
      <span className="absolute left-0 flex size-9 -translate-x-1/2 items-center justify-center rounded-full border border-border bg-card ring-4 ring-background">
        <MerchantIcon merchant={expense.merchant} className="size-4 text-muted-foreground" />
      </span>
      <div className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-card">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {expense.merchant ?? 'Sem estabelecimento'}
          </p>
          <p className="truncate text-xs text-muted-foreground">{details}</p>
        </div>
        {expense.amount === null ? (
          <Badge variant="secondary" className="font-normal text-amber-400">Sem valor</Badge>
        ) : (
          <span className="shrink-0 text-sm font-medium tabular-nums text-foreground">
            {formatCurrency(expense.amount)}
          </span>
        )}
      </div>
    </li>
  )
}

/* ── Resumo ─────────────────────────────────────────────────────────────── */

function SummaryView({ summary, month }: { summary: Summary; month: string }) {
  const thisMonth = currentMonth()
  // Average per elapsed day: the whole month once it's over, up to today otherwise.
  const elapsedDays = month === thisMonth ? Number(dayKey(new Date()).slice(8)) : summary.daily.length
  const perDay = summary.total / Math.max(elapsedDays, 1)

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Gastos" value={String(summary.count)}
          hint={summary.missingAmount ? `${summary.missingAmount} sem valor` : 'no mês'} />
        <StatTile label="Média por gasto" value={formatCurrency(summary.average)} hint="ticket médio" />
        <StatTile label="Média por dia" value={formatCurrency(perDay)}
          hint={`em ${elapsedDays} ${elapsedDays === 1 ? 'dia' : 'dias'}`} />
        <StatTile
          label="Maior gasto"
          value={summary.largest ? formatCurrency(summary.largest.amount ?? 0) : '—'}
          hint={summary.largest?.merchant ?? ''}
        />
      </div>

      <DailyChart daily={summary.daily} />

      <div className="grid gap-3 lg:grid-cols-2">
        <SharePanel
          title="Por categoria"
          note="Classificação automática em breve"
          shares={summary.byCategory}
        />
        <SharePanel title="Por cartão" shares={summary.byCard} />
        <SharePanel
          title="Principais estabelecimentos"
          shares={summary.topMerchants}
          withIcons
          className="lg:col-span-2"
        />
      </div>
    </div>
  )
}

function Panel({ title, note, className, children }: {
  title: string
  note?: string
  className?: string
  children: ReactNode
}) {
  return (
    <section className={cn('rounded-xl border border-border bg-card p-4', className)}>
      <div className="mb-4 flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        {note && <span className="text-xs text-muted-foreground">{note}</span>}
      </div>
      {children}
    </section>
  )
}

function StatTile({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-xl font-semibold tracking-tight text-foreground">{value}</p>
      <p className="mt-0.5 truncate text-xs text-muted-foreground">{hint || ' '}</p>
    </div>
  )
}

function DailyChart({ daily }: { daily: number[] }) {
  const max = Math.max(...daily, 0)
  const peak = daily.indexOf(max)
  const [active, setActive] = useState<number | null>(null)
  // The readout shows the hovered/tapped day, or the peak day by default.
  const shown = active ?? peak

  return (
    <Panel title="Gastos por dia">
      <p className="-mt-2 mb-3 text-xs text-muted-foreground">
        Dia {shown + 1}
        <span className="ml-2 font-medium tabular-nums text-foreground">{formatCurrency(daily[shown] ?? 0)}</span>
        {active === null && max > 0 && <span className="ml-2">· maior do mês</span>}
      </p>
      <div
        className="flex h-28 items-end gap-[2px] border-b border-border"
        onMouseLeave={() => setActive(null)}
      >
        {daily.map((value, i) => (
          <button
            key={i}
            type="button"
            aria-label={`Dia ${i + 1}: ${formatCurrency(value)}`}
            onMouseEnter={() => setActive(i)}
            onFocus={() => setActive(i)}
            onClick={() => setActive(i)}
            onBlur={() => setActive(null)}
            className="flex h-full max-w-6 flex-1 items-end outline-none"
          >
            <span
              className={cn(
                'w-full rounded-t-[4px] transition-colors',
                value > 0 ? 'bg-foreground/70' : 'bg-transparent',
                i === shown && value > 0 && 'bg-foreground',
              )}
              style={{ height: max > 0 ? `${(value / max) * 100}%` : 0 }}
            />
          </button>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[0.65rem] tabular-nums text-muted-foreground">
        <span>1</span>
        <span>{Math.ceil(daily.length / 2)}</span>
        <span>{daily.length}</span>
      </div>
    </Panel>
  )
}

function SharePanel({ title, note, shares, withIcons, className }: {
  title: string
  note?: string
  shares: Share[]
  withIcons?: boolean
  className?: string
}) {
  const max = Math.max(...shares.map((s) => s.total), 0)
  return (
    <Panel title={title} note={note} className={className}>
      <ul className="flex flex-col gap-3.5">
        {shares.map((share) => {
          return (
            <li key={share.name}>
              <div className="mb-1.5 flex items-center gap-2 text-sm">
                {withIcons && (
                  <MerchantIcon merchant={share.name} className="size-4 shrink-0 text-muted-foreground" />
                )}
                <span className="min-w-0 flex-1 truncate text-foreground">{share.name}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {share.count} {share.count === 1 ? 'gasto' : 'gastos'}
                </span>
                <span className="w-24 shrink-0 text-right font-medium tabular-nums text-foreground">
                  {formatCurrency(share.total)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-foreground/70"
                  style={{ width: max > 0 ? `${(share.total / max) * 100}%` : 0 }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </Panel>
  )
}
