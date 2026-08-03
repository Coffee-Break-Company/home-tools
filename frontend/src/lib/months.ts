export const MONTH_NAMES_SHORT = [
  'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
]

export const MONTH_NAMES_FULL = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]

/**
 * Formats an ISO date ('2026-08-03') as 'Ago/2026'.
 *
 * Split by hand instead of `new Date(iso)`, which parses as UTC and would land
 * on the previous month for early-in-the-month dates in BRT.
 */
export function formatMonthYear(isoDate: string): string {
  const [year, month] = isoDate.split('-')
  return `${MONTH_NAMES_SHORT[Number(month) - 1]}/${year}`
}

/** The current month as an `<input type="month">` value ('2026-08'). */
export function currentMonthValue(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}
