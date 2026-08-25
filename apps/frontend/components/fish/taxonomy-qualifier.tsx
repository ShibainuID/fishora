import { WarningCircle } from '@phosphor-icons/react/dist/ssr'
import type { TaxonomyStatus } from '@/lib/api/fish'

// Anything other than VERIFIED_TAXONOMY must stay visible beside the name.
export interface TaxonomyQualifierProps {
  status: TaxonomyStatus
  label: string
}

const COPY: Record<Exclude<TaxonomyStatus, 'VERIFIED_TAXONOMY'>, string> = {
  TAXONOMY_REVIEW_REQUIRED:
    'Nama ilmiah memerlukan tinjauan ahli. Identifikasi ini belum dikunci ke satu spesies.',
  MEDIUM_CONFIDENCE_LABEL_AMBIGUITY:
    'Label ini dipakai untuk lebih dari satu spesies. Konfirmasi ahli tetap diperlukan.',
  MIXED_TAXONOMY:
    'Taksonomi dikunci pada tingkat genus. Spesies pasti belum ditentukan.',
}

const TUNA_MIXED =
  'Taksonomi dikunci pada tingkat genus Thunnus spp. sampai verifikasi ahli.'

export function TaxonomyQualifier({ status, label }: TaxonomyQualifierProps) {
  if (status === 'VERIFIED_TAXONOMY') return null

  const message =
    status === 'MIXED_TAXONOMY' && label === 'tuna' ? TUNA_MIXED : COPY[status]

  return (
    <p className="text-body-sm flex items-start gap-1.5 text-state-warn">
      <WarningCircle className="mt-0.5 size-4 shrink-0" weight="fill" aria-hidden />
      <span>{message}</span>
    </p>
  )
}
