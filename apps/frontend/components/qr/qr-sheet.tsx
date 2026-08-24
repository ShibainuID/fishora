'use client'

import { useState } from 'react'
import Link from 'next/link'
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
  // No store listing exists, so the app link lands on the site root unless overridden.
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || '/'
  const [copied, setCopied] = useState(false)

  return (
    <Sheet open={open} onClose={onClose} title="Fishora QR">
      <section data-testid="qr-code-fish">
        <h3 className="text-label text-ink">Kode ikan ini</h3>
        <p className="text-body-sm mt-1 text-ink-muted">
          Pindai untuk membuka profil {speciesName}.
        </p>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt={`Kode QR profil ${speciesName}`}
          src={`/api/qr/${slug}`}
          className="mx-auto mt-4 size-40"
        />
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
      </section>

      <section data-testid="qr-code-app" className="mt-6 border-t border-line pt-4">
        <h3 className="text-label text-ink">Kode Fishora</h3>
        <p className="text-body-sm mt-1 text-ink-muted">
          Cetak kode ini di kartu yang sama. Kode ini membuka Fishora, bukan profil ikan.
        </p>
        {/* eslint-disable-next-line @next/next/no-img-element -- generated PNG from our own route */}
        <img
          src="/api/qr/app"
          alt="Kode QR untuk membuka Fishora"
          width={160}
          height={160}
          className="mt-3 rounded-2xl bg-surface-raised p-2"
        />
        <Link
          href={appUrl}
          className="text-body-sm mt-3 flex min-h-11 items-center text-ink underline"
        >
          Buka Fishora
        </Link>
      </section>
    </Sheet>
  )
}
