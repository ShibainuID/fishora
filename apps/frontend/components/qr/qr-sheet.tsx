'use client'

import { useState } from 'react'
import { Printer } from '@phosphor-icons/react/dist/ssr'
import { Sheet } from '@/components/common/sheet'
import { QrCard } from '@/components/qr/qr-card'
import { discoverUrl } from '@/lib/qr'
import type { components } from '@/lib/api/schema'

type Lot = components['schemas']['LotResponse']

export function QrSheet({
  open,
  onClose,
  lot,
}: {
  open: boolean
  onClose: () => void
  lot: Lot
}) {
  const url = discoverUrl(lot.public_slug)
  const [copied, setCopied] = useState(false)

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Fishora QR"
      variant="modal"
      actions={
        <button
          type="button"
          // Hands off to the device: the operator picks the printer, the paper
          // and the copies, and a kiosk or a phone share sheet works the same.
          onClick={() => window.print()}
          aria-label="Cetak kartu"
          title="Cetak kartu"
          className="grid size-11 shrink-0 place-items-center rounded-full text-ink-muted transition-colors hover:bg-bg-sunken hover:text-ink active:scale-[0.98]"
        >
          <Printer className="size-5" aria-hidden />
        </button>
      }
      footer={
        <div className="flex items-center gap-2">
          <input
            readOnly
            aria-label="URL"
            value={url}
            className="text-body-sm min-h-11 min-w-0 flex-1 rounded-[var(--radius-input)] border border-line-input bg-transparent px-3 text-ink"
          />
          <button
            type="button"
            onClick={async () => {
              await navigator.clipboard.writeText(url)
              setCopied(true)
            }}
            className="text-body-sm min-h-11 shrink-0 rounded-full border border-line-strong px-4 text-ink"
          >
            {copied ? 'Disalin' : 'Salin URL'}
          </button>
        </div>
      }
    >
      <QrCard lot={lot} />
    </Sheet>
  )
}
