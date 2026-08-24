'use client'

import { useState } from 'react'
import { Button } from '@/components/common/button'
import { Sheet } from '@/components/common/sheet'
import { QrSheet } from '@/components/qr/qr-sheet'
import { allocateLot, closeLot } from '@/lib/api/commerce'
import { rupiahPerKg } from '@/lib/format'
import type { components } from '@/lib/api/schema'

type Lot = components['schemas']['LotResponse']
type Pending = { lot: Lot; kind: 'allocate' | 'close' }

export function OperatorLots({ lots }: { lots: Lot[] }) {
  const [items, setItems] = useState(lots)
  const [pending, setPending] = useState<Pending | null>(null)
  const [qr, setQr] = useState<Lot | null>(null)
  const closing = pending?.kind === 'close'
  const allocating = pending?.kind === 'allocate'

  return (
    <main className="px-4 py-6 pb-24">
      <h1 className="text-h1 text-ink">Lot saya</h1>
      <ul className="mt-6 flex flex-col gap-4">
        {items.map((lot) => (
          <li key={lot.id} className="rounded-2xl border border-line p-4">
            <p className="text-h3 text-ink">{lot.species_id.replace('species_', '')}</p>
            <p className="text-body-sm text-ink-muted">{lot.status}</p>
            {lot.status === 'active' && (
              <Button type="button" className="mt-3" onClick={() => setPending({ lot, kind: 'close' })}>
                Tutup lelang
              </Button>
            )}
            {lot.status === 'closed' && (
              <Button type="button" className="mt-3" onClick={() => setPending({ lot, kind: 'allocate' })}>
                Allocate to winning bidder
              </Button>
            )}
            {lot.status === 'allocated' && (
              <Button type="button" variant="secondary" className="mt-3" onClick={() => setQr(lot)}>
                Buat QR
              </Button>
            )}
          </li>
        ))}
      </ul>
      <Sheet
        open={Boolean(pending)}
        onClose={() => setPending(null)}
        title={closing ? 'Konfirmasi tutup lelang' : 'Konfirmasi alokasi'}
        footer={
          <Button
            block
            type="button"
            onClick={async () => {
              if (!pending) return
              if (pending.kind === 'close') {
                await closeLot(pending.lot.id)
                setItems((current) =>
                  current.map((item) =>
                    item.id === pending.lot.id ? { ...item, status: 'closed' } : item
                  )
                )
                setPending(null)
                return
              }
              await allocateLot(pending.lot.id)
              setQr(pending.lot)
              setPending(null)
            }}
          >
            {closing ? 'Konfirmasi tutup' : 'Konfirmasi'}
          </Button>
        }
      >
        {closing && pending && (
          <p className="text-body text-ink">
            Tutup lelang ini sekarang? Pembeli tidak bisa mengajukan tawaran baru.
          </p>
        )}
        {allocating && pending && (
          <p className="text-body text-ink">
            Alokasikan ke Dewi Anggraini sebesar {rupiahPerKg(Number(pending.lot.current_highest_per_kg ?? pending.lot.starting_price_per_kg))}?
          </p>
        )}
      </Sheet>
      {qr && (
        <QrSheet
          open
          onClose={() => setQr(null)}
          slug={qr.public_slug}
          speciesName={qr.species_id.replace('species_', '')}
        />
      )}
    </main>
  )
}
