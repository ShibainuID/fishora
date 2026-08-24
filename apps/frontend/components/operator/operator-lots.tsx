'use client'

import { useState } from 'react'
import { Button } from '@/components/common/button'
import { Sheet } from '@/components/common/sheet'
import { QrSheet } from '@/components/qr/qr-sheet'
import { allocateLot } from '@/lib/api/commerce'
import { rupiahPerKg } from '@/lib/format'
import type { components } from '@/lib/api/schema'

type Lot = components['schemas']['LotResponse']

export function OperatorLots({ lots }: { lots: Lot[] }) {
  const [confirm, setConfirm] = useState<Lot | null>(null)
  const [qr, setQr] = useState<Lot | null>(null)

  return (
    <main className="px-4 py-6 pb-24">
      <h1 className="text-h1 text-ink">Lot saya</h1>
      <ul className="mt-6 flex flex-col gap-4">
        {lots.map((lot) => (
          <li key={lot.id} className="rounded-2xl border border-line p-4">
            <p className="text-h3 text-ink">{lot.species_id.replace('species_', '')}</p>
            <p className="text-body-sm text-ink-muted">{lot.status}</p>
            {lot.status === 'closed' && (
              <Button type="button" className="mt-3" onClick={() => setConfirm(lot)}>
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
        open={Boolean(confirm)}
        onClose={() => setConfirm(null)}
        title="Konfirmasi alokasi"
        footer={
          <Button
            block
            type="button"
            onClick={async () => {
              if (!confirm) return
              await allocateLot(confirm.id)
              setQr(confirm)
              setConfirm(null)
            }}
          >
            Konfirmasi
          </Button>
        }
      >
        {confirm && (
          <p className="text-body text-ink">
            Alokasikan ke Dewi Anggraini sebesar {rupiahPerKg(Number(confirm.current_highest_per_kg ?? confirm.starting_price_per_kg))}?
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
