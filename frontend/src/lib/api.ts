import { supabase } from './supabase'

const base = import.meta.env.VITE_API_URL ?? ''

async function authHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }
  return headers
}

export const api = {
  get: async (path: string) =>
    fetch(`${base}${path}`, { headers: await authHeaders() }),
  post: async (path: string, body: unknown) =>
    fetch(`${base}${path}`, {
      method: 'POST',
      headers: await authHeaders(),
      body: JSON.stringify(body),
    }),
  delete: async (path: string) =>
    fetch(`${base}${path}`, { method: 'DELETE', headers: await authHeaders() }),
}
