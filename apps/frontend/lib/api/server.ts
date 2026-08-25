import 'server-only'

import { cookies } from 'next/headers'
import { apiFetch, type ApiFetchOptions } from './client'
import type { Lot, MatchReason } from './commerce'

// A Server Component fetch carries no browser cookies of its own, so an authed
// endpoint reached from an RSC looks anonymous unless the session is forwarded
// explicitly. Without this, "my lots" is really "everyone's lots".
async function withSession(init: ApiFetchOptions = {}): Promise<ApiFetchOptions> {
  const jar = await cookies()
  const cookie = jar
    .getAll()
    .map((entry) => `${entry.name}=${entry.value}`)
    .join('; ')
  return cookie ? { ...init, headers: { ...init.headers, cookie } } : init
}

export async function getMeAsServer() {
  return apiFetch<{ id: string; role: string; name: string; username: string }>(
    '/api/v1/auth/me',
    await withSession()
  )
}

export async function getRecommendationsAsServer(buyerId: string) {
  return apiFetch<{
    items: { lot: Lot; score: number; reasons: MatchReason[] }[]
    profile_missing: boolean
  }>(`/api/v1/buyers/${encodeURIComponent(buyerId)}/recommendations`, await withSession())
}

export async function listMyLotsAsServer(query = '') {
  const suffix = query ? `?${query}` : ''
  return apiFetch<Lot[]>(`/api/v1/lots${suffix}`, await withSession())
}
