const base = import.meta.env.VITE_API_URL ?? ''

export const api = {
  get: (path: string) => fetch(`${base}${path}`),
  post: (path: string, body: unknown) =>
    fetch(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  delete: (path: string) => fetch(`${base}${path}`, { method: 'DELETE' }),
}
