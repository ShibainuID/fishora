import { http, HttpResponse } from 'msw'
import { BIDS, CARD, LOTS, REASONS, lotFixture } from './fixtures'

const API = 'http://localhost:8000'

export const handlers = [
  http.post(`${API}/api/v1/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { username: string }
    const operator = body.username === 'rian'
    return HttpResponse.json({
      id: operator ? 'op_rian' : 'buyer_dewi',
      role: operator ? 'operator' : 'buyer',
      name: operator ? 'Rian Setiawan' : 'Dewi Anggraini',
      username: body.username,
    })
  }),

  http.post(`${API}/api/v1/auth/logout`, () => HttpResponse.json({ ok: true })),

  http.get(`${API}/api/v1/auth/me`, () =>
    HttpResponse.json({
      id: 'buyer_dewi',
      role: 'buyer',
      name: 'Dewi Anggraini',
      username: 'dewi',
    })
  ),

  http.post(`${API}/api/v1/lots`, async ({ request }) => {
    const body = (await request.json()) as {
      prediction_id: string
      quantity_kg: string
      starting_price_per_kg: string
      size_category: 'S' | 'M' | 'L'
      landing_point_id: string
    }
    return HttpResponse.json(
      lotFixture({
        prediction_id: body.prediction_id,
        quantity_kg: body.quantity_kg,
        starting_price_per_kg: body.starting_price_per_kg,
        size_category: body.size_category,
        landing_point_id: body.landing_point_id,
        status: 'active',
      })
    )
  }),

  http.get(`${API}/api/v1/lots`, ({ request }) => {
    const url = new URL(request.url)
    const species = url.searchParams.get('species_id')
    const status = url.searchParams.get('status')
    let rows = LOTS
    if (species) rows = rows.filter((lot) => lot.species_id === species)
    if (status) rows = rows.filter((lot) => lot.status === status)
    return HttpResponse.json(rows)
  }),

  http.get(`${API}/api/v1/lots/:id`, ({ params }) => {
    const lot = LOTS.find((row) => row.id === params.id) ?? lotFixture({ id: String(params.id) })
    return HttpResponse.json(lot)
  }),

  http.get(`${API}/api/v1/lots/:id/bids`, () => HttpResponse.json(BIDS)),

  http.post(`${API}/api/v1/lots/:id/bids`, async ({ request }) => {
    const body = (await request.json()) as { amount_per_kg: string }
    const amount = Number(body.amount_per_kg)
    if (amount <= 70000) {
      return HttpResponse.json(
        { detail: 'bid must exceed current highest', current_highest_per_kg: '70000.00' },
        { status: 409 }
      )
    }
    return HttpResponse.json({
      id: 'bid_new',
      lot_id: 'lot_tenggiri_1',
      buyer_id: 'buyer_dewi',
      amount_per_kg: body.amount_per_kg,
      created_at: '2026-08-24T11:00:00+00:00',
    })
  }),

  http.post(`${API}/api/v1/lots/:id/close`, ({ params }) =>
    HttpResponse.json(lotFixture({ id: String(params.id), status: 'closed' }))
  ),

  http.post(`${API}/api/v1/lots/:id/allocate`, () =>
    HttpResponse.json({
      id: 'lot_tenggiri_1',
      status: 'allocated',
      allocated_buyer_id: 'buyer_dewi',
      current_highest_per_kg: '70000.00',
    })
  ),

  http.put(`${API}/api/v1/buyers/:id/preferences`, async ({ request, params }) => {
    const body = await request.json()
    return HttpResponse.json({ buyer_id: params.id, ...(body as object) })
  }),

  http.get(`${API}/api/v1/buyers/:id/recommendations`, () =>
    HttpResponse.json({
      profile_missing: false,
      items: [{ lot: LOTS[0], score: 0.9, reasons: REASONS }],
    })
  ),

  http.get(`${API}/api/v1/discover/:slug`, ({ params }) => {
    if (params.slug === 'missing') return HttpResponse.json({ detail: 'not found' }, { status: 404 })
    return HttpResponse.json({
      public_slug: params.slug,
      species_id: 'species_tenggiri',
      card: CARD,
    })
  }),
]
