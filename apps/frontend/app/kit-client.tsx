'use client'

import { useState } from 'react'
import { Button } from '@/components/common/button'
import { Field } from '@/components/common/field'
import { Sheet } from '@/components/common/sheet'

/** Client islands for the foundations preview. Temporary, see app/page.tsx. */

export function KitFields() {
  const [price, setPrice] = useState('68000')

  return (
    <div className="flex max-w-[26rem] flex-col gap-4">
      <Field
        label="Jumlah"
        inputMode="numeric"
        suffix="kg"
        placeholder="24"
        helper="Berat total lot ini."
      />
      <Field
        label="Harga awal per kg"
        inputMode="numeric"
        prefix="Rp"
        value={price}
        onChange={(e) => setPrice(e.target.value)}
      />
      <Field
        label="Harga awal per kg"
        inputMode="numeric"
        prefix="Rp"
        defaultValue="0"
        error="Harga awal harus lebih dari nol."
      />
    </div>
  )
}

export function KitSheet() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Open sheet
      </Button>
      <Sheet
        open={open}
        onClose={() => setOpen(false)}
        title="Filters"
        footer={
          <Button block size="lg" onClick={() => setOpen(false)}>
            Show 12 lots
          </Button>
        }
      >
        <div className="flex flex-col gap-4">
          <Field label="Harga maksimum per kg" inputMode="numeric" prefix="Rp" placeholder="70000" />
          <Field label="Jumlah minimum" inputMode="numeric" suffix="kg" placeholder="20" />
          <p className="text-body-sm text-ink-muted">
            Groups are collapsed by default except the two most used, so the
            sheet opens showing options rather than headings.
          </p>
        </div>
      </Sheet>
    </>
  )
}
