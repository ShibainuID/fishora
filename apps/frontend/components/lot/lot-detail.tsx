'use client'

import { useState } from 'react'
import { KnowledgeCardView } from '@/components/fish/knowledge-card'
import { MarketSignals } from '@/components/fish/market-signals'
import { SpeciesArt } from '@/components/fish/species-art'
import { SpeciesHeader } from '@/components/fish/species-header'
import { Button } from '@/components/common/button'
import { Field } from '@/components/common/field'
import { Sheet } from '@/components/common/sheet'
import { ReviewForm } from '@/components/buyer/review-form'
import { MatchReasons } from '@/components/lot/match-reasons'
import { Countdown } from '@/components/lot/countdown'
import { ApiError } from '@/lib/api/errors'
import { placeBid, type Review } from '@/lib/api/commerce'
import { kilograms, rupiahPerKg } from '@/lib/format'
import { Z } from '@/lib/z'
import type { components } from '@/lib/api/schema'
import type { KnowledgeCard } from '@/lib/api/fish'

type Lot = components['schemas']['LotResponse']
type Reason = components['schemas']['MatchReasonResponse']

export function LotDetail({
  lot,
  card,
  reasons,
  reviews,
  canReview = false,
  photoUrl,
}: {
  lot: Lot
  card: KnowledgeCard
  reasons: Reason[]
  reviews: Review[]
  /** Only the buyer holding the allocation may write one. */
  canReview?: boolean
  /** A real photograph when one exists. Falls back to the species composition. */
  photoUrl?: string
}) {
  const [posted, setPosted] = useState<Review[]>([])
  const [highest, setHighest] = useState(Number(lot.current_highest_per_kg ?? lot.starting_price_per_kg))
  const [amount, setAmount] = useState(String(highest + 1000))
  const [sheetOpen, setSheetOpen] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const closed = lot.status !== 'active'
  const label = lot.species_id.replace('species_', '')

  const submit = async () => {
    const value = Number(amount)
    if (value <= highest) {
      setError('Penawaran harus di atas harga tertinggi saat ini.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const bid = await placeBid(lot.id, amount)
      setHighest(Number(bid.amount_per_kg))
      setSheetOpen(false)
    } catch (cause) {
      if (cause instanceof ApiError && cause.kind === 'outbid' && cause.currentHighestPerKg) {
        const next = Number(cause.currentHighestPerKg)
        setHighest(next)
        setAmount(String(next + 1000))
        setError(`Harga tertinggi sekarang ${rupiahPerKg(next)}`)
      } else if (cause instanceof ApiError) {
        setError(cause.userMessage)
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div data-page="lot-detail" className="flex flex-col gap-6 px-4 pb-28 lg:pb-8">
      <SpeciesHeader label={label} verified />
      {reasons.length > 0 && (
        <div className="lg:hidden">
          <MatchReasons reasons={reasons} />
        </div>
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {photoUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- operator upload, arbitrary origin
        <img src={photoUrl} alt="" className="aspect-[4/3] w-full rounded-2xl object-cover" />
      ) : (
        <SpeciesArt
          label={lot.species_id.replace('species_', '')}
          className="aspect-[4/3] w-full rounded-2xl"
        />
      )}
      <dl className="grid grid-cols-2 gap-3">
        <div>
          <dt className="text-label text-ink-muted">Volume</dt>
          <dd className="text-num-sm tabular-nums text-ink">{kilograms(Number(lot.quantity_kg))}</dd>
        </div>
        <div>
          <dt className="text-label text-ink-muted">Harga awal</dt>
          <dd className="text-num-sm tabular-nums text-ink">{rupiahPerKg(Number(lot.starting_price_per_kg))}</dd>
        </div>
      </dl>
      <KnowledgeCardView card={card} label={label} />
      <MarketSignals reviews={[...posted, ...reviews]} />
      {canReview && <ReviewForm lotId={lot.id} onSubmitted={(review) => setPosted((current) => [review, ...current])} />}

      <div
        className="fixed inset-x-0 bottom-0 flex items-center justify-between gap-3 border-t border-line bg-surface px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:hidden"
        style={{ zIndex: Z.actionBar }}
      >
        {closed ? (
          <p className="text-body text-ink">Lelang selesai. {rupiahPerKg(highest)}</p>
        ) : (
          <>
            <div>
              <p className="text-num-lg tabular-nums text-ink">{rupiahPerKg(highest)}</p>
              <Countdown endsAt={lot.auction_ends_at} />
            </div>
            <Button type="button" onClick={() => setSheetOpen(true)}>
              Ajukan penawaran
            </Button>
          </>
        )}
      </div>

      <Sheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        title="Ajukan penawaran"
        footer={
          <Button block type="button" loading={busy} onClick={submit}>
            Kirim
          </Button>
        }
      >
        <Field
          label="Harga per kg"
          prefix="Rp"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          error={error || undefined}
        />
      </Sheet>
    </div>
  )
}
