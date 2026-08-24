'use client'

import { useState } from 'react'
import { Button } from '@/components/common/button'
import { Sheet } from '@/components/common/sheet'
import { QR_EXPORTS, discoverUrl } from '@/lib/qr'

export function QrSheet({
  open,
  onClose,
  slug,
  speciesName,
}: {
  open: boolean
  onClose: () => void
  slug: string
  speciesName: string
}) {
  const url = discoverUrl(slug)
  const [copied, setCopied] = useState(false)

  return (
    <Sheet open={open} onClose={onClose} title="Fishora QR">
      <p className="text-body text-ink">{speciesName}. Pindai untuk membuka profil.</p>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img alt="QR" src={`/api/qr/${slug}`} className="mx-auto mt-4 size-40" />
      <label className="text-label mt-4 block text-ink">
        URL
        <input readOnly value={url} className="mt-2 min-h-11 w-full rounded-[var(--radius-input)] border border-line px-3" />
      </label>
      <Button
        type="button"
        variant="secondary"
        className="mt-3"
        onClick={async () => {
          await navigator.clipboard.writeText(url)
          setCopied(true)
        }}
      >
        {copied ? 'Disalin' : 'Salin URL'}
      </Button>
      <ul className="mt-6 flex flex-col gap-2">
        {QR_EXPORTS.map((item) => (
          <li key={item.id}>
            <a
              href={`/api/qr/${slug}?size=${item.mm}`}
              data-size={item.mm}
              className="text-body-sm flex min-h-11 items-center text-ink"
            >
              {item.label} {item.mm}mm
            </a>
          </li>
        ))}
      </ul>
    </Sheet>
  )
}
